"""Recursive-descent disassembler with linear-sweep fallback and prologue discovery."""

from __future__ import annotations

import struct
from collections import deque
from dataclasses import dataclass

import capstone

from core.arch import ArchProfile, get_arch_profile
from core.loader import LoadedELF
from core.models import Instruction, JumpTable, Section, Symbol

_NON_RETURNING_IMPORTS: frozenset[str] = frozenset(
    {
        "abort",
        "exit",
        "_exit",
        "_Exit",
        "__stack_chk_fail",
        "__assert_fail",
        "__cxa_throw",
        "__cxa_rethrow",
        "longjmp",
        "siglongjmp",
        "err",
        "errx",
        "verr",
        "verrx",
    }
)


@dataclass(frozen=True, slots=True)
class DisassemblyResult:
    """Output of the .text disassembly pipeline."""

    instructions: dict[int, Instruction]
    function_starts: tuple[int, ...]
    symbol_functions: dict[int, Symbol]
    jump_tables: dict[int, JumpTable]


def _decode_single(
    md: capstone.Cs,
    profile: ArchProfile,
    code: bytes,
    vaddr: int,
) -> Instruction | None:
    """Decode a single instruction at the start of `code`."""
    for cs_insn in md.disasm(code[:16], vaddr, count=1):
        branch_target, call_target, rip_target = profile.extract_targets(cs_insn)
        groups = tuple(str(md.group_name(g)) for g in cs_insn.groups)
        return Instruction(
            addr=int(cs_insn.address),
            size=int(cs_insn.size),
            mnemonic=str(cs_insn.mnemonic).lower(),
            op_str=str(cs_insn.op_str),
            raw_bytes=bytes(cs_insn.bytes),
            groups=groups,
            branch_target=branch_target,
            call_target=call_target,
            rip_target=rip_target,
        )
    return None


def _collect_symbol_functions(
    loaded: LoadedELF,
    text_sec: Section,
) -> dict[int, Symbol]:
    """Collect STT_FUNC symbols residing inside .text, preferring .symtab over .dynsym."""
    by_addr: dict[int, Symbol] = {}
    for sym in loaded.binary.symbols:
        if sym.sym_type != "STT_FUNC":
            continue
        if not text_sec.contains(sym.addr):
            continue
        existing = by_addr.get(sym.addr)
        if existing is None or (existing.is_dynamic and not sym.is_dynamic):
            by_addr[sym.addr] = sym
    return by_addr


def _parse_cmp_bound(insns_before: list[Instruction]) -> int | None:
    """Extract upper switch index bound from a recent `cmp ..., imm` + conditional branch."""
    for idx in range(len(insns_before) - 1, -1, -1):
        insn = insns_before[idx]
        if insn.mnemonic not in ("cmp", "sub"):
            continue
        parts = [p.strip() for p in insn.op_str.split(",")]
        if len(parts) != 2:
            continue
        imm_str = parts[1]
        try:
            imm_val = int(imm_str, 0)
        except ValueError:
            continue
        if imm_val <= 0 or imm_val > 1024:
            continue
        # Look for the conditional jump immediately following the comparison
        for next_insn in insns_before[idx + 1 : idx + 5]:
            if next_insn.mnemonic in ("ja", "jg", "jbe", "jle"):
                return imm_val + 1
            if next_insn.mnemonic in ("jae", "jge", "jb", "jl"):
                return imm_val
        return imm_val + 1
    return None


def _extract_scaled_base_reg(op_str: str) -> tuple[str | None, int]:
    """Extract (base_reg, scale) from a memory operand like `dword ptr [r13 + rax*4]`."""
    if "[" not in op_str or "]" not in op_str:
        return None, 0
    mem_part = op_str.split("[", 1)[1].split("]", 1)[0]
    scale = 4 if "*4" in mem_part else (8 if "*8" in mem_part else 0)
    if scale == 0:
        return None, 0
    tokens = [t.strip() for t in mem_part.replace("-", "+").split("+")]
    for tok in tokens:
        if "*" not in tok and tok.isalnum() and not tok.isdigit():
            return tok, scale
    return None, scale


def resolve_jump_table(
    jmp_insn: Instruction,
    recent_insns: list[Instruction],
    loaded: LoadedELF,
    text_sec: Section,
    func_min_addr: int,
    func_max_addr: int,
    rodata_boundaries: tuple[int, ...] = (),
) -> JumpTable | None:
    """Best-effort resolution of an x86-64 PIC relative or absolute jump table."""
    if not recent_insns:
        return None

    short_window = [i for i in recent_insns if jmp_insn.addr - 160 <= i.addr < jmp_insn.addr]
    if not short_window:
        return None

    # 1. Identify scaled index load (*4 or *8) and its base register near the indirect jump
    base_reg: str | None = None
    entry_size = 0
    for cand in reversed(short_window[-12:]):
        reg, scale = _extract_scaled_base_reg(cand.op_str)
        if scale in (4, 8):
            base_reg = reg
            entry_size = scale
            break
    if entry_size == 0:
        reg, scale = _extract_scaled_base_reg(jmp_insn.op_str)
        if scale in (4, 8):
            base_reg = reg
            entry_size = scale
    if entry_size == 0:
        return None

    # 2. Search backward for `lea <base_reg>, [rip + disp]` (including LICM-hoisted LEAs)
    table_addr: int | None = None
    if base_reg is not None:
        prefix = f"{base_reg},"
        for cand in reversed(recent_insns):
            if (
                cand.mnemonic == "lea"
                and cand.rip_target is not None
                and cand.op_str.startswith(prefix)
            ):
                table_addr = cand.rip_target
                break

    # Fallback: closest `lea reg, [rip + disp]` within short_window
    if table_addr is None:
        for cand in reversed(short_window):
            if cand.mnemonic == "lea" and cand.rip_target is not None:
                table_addr = cand.rip_target
                break

    if table_addr is None:
        return None

    bound = _parse_cmp_bound(short_window)
    max_entries = bound if bound is not None else 256

    # Cap max_entries if another known .rodata reference starts after `table_addr`
    for boundary in rodata_boundaries:
        if boundary > table_addr:
            avail_entries = (boundary - table_addr) // entry_size
            if avail_entries < max_entries:
                max_entries = avail_entries
            break

    if max_entries <= 0:
        return None

    targets: list[int] = []
    for idx in range(max_entries):
        entry_vaddr = table_addr + idx * entry_size
        raw_entry = loaded.read_vaddr(entry_vaddr, entry_size)
        if raw_entry is None:
            break
        if entry_size == 4:
            rel_offset = struct.unpack_from("<i", raw_entry, 0)[0]
            target = (table_addr + rel_offset) & 0xFFFFFFFFFFFFFFFF
        else:
            target = struct.unpack_from("<Q", raw_entry, 0)[0]

        if not text_sec.contains(target):
            break
        if not (func_min_addr <= target < func_max_addr):
            break
        targets.append(target)

    if not targets:
        return None

    return JumpTable(
        insn_addr=jmp_insn.addr,
        table_addr=table_addr,
        targets=tuple(targets),
    )


def _find_main_from_entry(
    instructions: dict[int, Instruction],
    entry_point: int,
    text_sec: Section,
) -> int | None:
    """In an executable's _start stub, extract `main` from `lea rdi, [rip + disp]`."""
    for addr in sorted(a for a in instructions if entry_point <= a < entry_point + 64):
        insn = instructions[addr]
        if (
            insn.mnemonic == "lea"
            and insn.op_str.startswith("rdi,")
            and insn.rip_target is not None
            and text_sec.contains(insn.rip_target)
        ):
            return insn.rip_target
    return None


def disassemble_text(loaded: LoadedELF) -> DisassemblyResult:
    """Disassemble .text using recursive descent with linear-sweep fallback."""
    binary = loaded.binary
    profile = get_arch_profile(binary.arch)
    md = profile.create_disassembler(binary.endian)

    text_sec = binary.get_section(".text")
    if text_sec is None or text_sec.size == 0:
        return DisassemblyResult(
            instructions={},
            function_starts=(),
            symbol_functions={},
            jump_tables={},
        )

    text_bytes = loaded.section_data.get(".text", b"")
    if not text_bytes:
        return DisassemblyResult(
            instructions={},
            function_starts=(),
            symbol_functions={},
            jump_tables={},
        )

    text_start = text_sec.addr
    text_end = text_sec.addr + len(text_bytes)
    non_ret_plt_addrs: set[int] = {
        imp.plt_addr
        for imp in binary.imports
        if imp.name in _NON_RETURNING_IMPORTS and imp.plt_addr != 0
    }

    symbol_functions = _collect_symbol_functions(loaded, text_sec)
    discovered_func_starts: set[int] = set(symbol_functions.keys())

    # Seed from ELF entry point if inside .text
    if text_sec.contains(binary.entry_point):
        discovered_func_starts.add(binary.entry_point)

    # Seed from R_*_RELATIVE relocation addends pointing to .text prologues/starts
    for reloc_addr in loaded.reloc_text_Addends:
        if text_sec.contains(reloc_addr):
            off = reloc_addr - text_start
            if profile.padding_length(text_bytes, off) == 0:
                discovered_func_starts.add(reloc_addr)

    instructions: dict[int, Instruction] = {}
    jump_tables: dict[int, JumpTable] = {}
    covered = bytearray(len(text_bytes))
    trace_queue: deque[int] = deque(sorted(discovered_func_starts))

    def _run_recursive_descent() -> None:
        while trace_queue:
            start_vaddr = trace_queue.popleft()
            if not (text_start <= start_vaddr < text_end):
                continue

            curr = start_vaddr
            recent_trace: list[Instruction] = []

            while text_start <= curr < text_end:
                off = curr - text_start
                if covered[off]:
                    break

                insn = _decode_single(md, profile, text_bytes[off : off + 16], curr)
                if insn is None or insn.size <= 0:
                    break

                # Ensure instruction does not overlap already-decoded bytes
                if any(covered[off : off + insn.size]):
                    break

                for b_idx in range(off, min(off + insn.size, len(covered))):
                    covered[b_idx] = 1
                instructions[insn.addr] = insn
                recent_trace.append(insn)

                if profile.is_call(insn):
                    ct = insn.call_target
                    if (
                        ct is not None
                        and text_start <= ct < text_end
                        and ct not in discovered_func_starts
                    ):
                        discovered_func_starts.add(ct)
                        trace_queue.append(ct)
                    if ct is not None and ct in non_ret_plt_addrs:
                        break
                    curr = insn.end_addr
                    continue

                if profile.is_ret(insn) or profile.is_trap_or_halt(insn):
                    break

                if profile.is_unconditional_jump(insn):
                    bt = insn.branch_target
                    if bt is not None:
                        if text_start <= bt < text_end and not covered[bt - text_start]:
                            trace_queue.append(bt)
                    elif profile.is_indirect_jump(insn):
                        # Determine enclosing function bounds for jump table validation
                        prior_starts = [s for s in discovered_func_starts if s <= insn.addr]
                        f_min = max(prior_starts) if prior_starts else text_start
                        later_starts = [s for s in discovered_func_starts if s > insn.addr]
                        f_max = min(later_starts) if later_starts else text_end
                        jt = resolve_jump_table(
                            insn,
                            recent_trace,
                            loaded,
                            text_sec,
                            f_min,
                            f_max,
                        )
                        if jt is not None:
                            jump_tables[insn.addr] = jt
                            for target in jt.targets:
                                if not covered[target - text_start]:
                                    trace_queue.append(target)
                    break

                if profile.is_conditional_jump(insn):
                    bt = insn.branch_target
                    if (
                        bt is not None
                        and text_start <= bt < text_end
                        and not covered[bt - text_start]
                    ):
                        trace_queue.append(bt)
                    curr = insn.end_addr
                    continue

                curr = insn.end_addr

    # Phase 1: Initial recursive descent from symbols, entry point, and relocations
    _run_recursive_descent()

    # Check if _start passed `main` in rdi to __libc_start_main
    if text_sec.contains(binary.entry_point):
        main_addr = _find_main_from_entry(instructions, binary.entry_point, text_sec)
        if main_addr is not None and main_addr not in discovered_func_starts:
            discovered_func_starts.add(main_addr)
            trace_queue.append(main_addr)
            _run_recursive_descent()

    # Phase 2: Linear-sweep fallback over uncovered .text gaps + prologue discovery
    # Build known symbol ranges [addr, addr + size) so we don't split symbol-backed functions
    known_sym_ranges: list[tuple[int, int]] = [
        (sym.addr, sym.addr + sym.size) for sym in symbol_functions.values() if sym.size > 0
    ]

    def _inside_known_sym_range(vaddr: int) -> bool:
        return any(lo < vaddr < hi for lo, hi in known_sym_ranges)

    off = 0
    text_len = len(text_bytes)
    while off < text_len:
        if covered[off]:
            off += 1
            continue

        # Skip inter-function alignment padding (NOPs, INT3, 0x00 bytes)
        pad_len = profile.padding_length(text_bytes, off)
        if pad_len > 0:
            for p_idx in range(off, min(off + pad_len, text_len)):
                covered[p_idx] = 1
            off += pad_len
            continue

        cand_addr = text_start + off
        # Determine whether this uncovered code region starts a new function
        is_prologue = profile.matches_prologue(text_bytes, off)
        inside_sym = _inside_known_sym_range(cand_addr)

        # Trace from `cand_addr` using recursive descent
        prev_func_starts = [s for s in discovered_func_starts if s < cand_addr]
        enclosing_start = max(prev_func_starts) if prev_func_starts else text_start

        before_addrs = set(instructions.keys())
        trace_queue.append(cand_addr)
        _run_recursive_descent()
        new_addrs = set(instructions.keys()) - before_addrs

        if not new_addrs:
            # Byte could not be decoded as valid instruction; mark covered and advance
            covered[off] = 1
            off += 1
            continue

        # Filter out pure NOP-only traces that appeared at the end of a gap
        non_nop_insns = [
            instructions[a] for a in sorted(new_addrs) if not profile.is_nop(instructions[a])
        ]
        if not non_nop_insns:
            for a in new_addrs:
                del instructions[a]
            off += 1
            continue

        first_real_addr = non_nop_insns[0].addr
        for a in new_addrs:
            if a < first_real_addr:
                del instructions[a]

        if not inside_sym and is_prologue:
            # Check if instructions in this trace jump back into the preceding function
            jumps_into_prev = False
            for a in new_addrs:
                if a not in instructions:
                    continue
                ins = instructions[a]
                bt = ins.branch_target
                if bt is not None and enclosing_start <= bt < first_real_addr:
                    jumps_into_prev = True
                    break
            if not jumps_into_prev and (first_real_addr % 16 == 0 or binary.is_stripped):
                discovered_func_starts.add(first_real_addr)
        elif binary.is_stripped and first_real_addr == text_start:
            # First executable code at the very start of .text (e.g. deregister_tm_clones)
            discovered_func_starts.add(first_real_addr)

        off = (first_real_addr - text_start) + 1

    # Re-resolve any indirect jumps whose targets may lie within finalized function bounds
    rodata_refs = tuple(
        sorted(
            {
                ins.rip_target
                for ins in instructions.values()
                if ins.rip_target is not None and not text_sec.contains(ins.rip_target)
            }
        )
    )
    sorted_starts = sorted(discovered_func_starts)
    sorted_insn_addrs = sorted(instructions.keys())

    for idx, f_start in enumerate(sorted_starts):
        f_end = sorted_starts[idx + 1] if idx + 1 < len(sorted_starts) else text_end
        func_insns = [instructions[a] for a in sorted_insn_addrs if f_start <= a < f_end]
        for i_pos, ins in enumerate(func_insns):
            if profile.is_indirect_jump(ins):
                jt = resolve_jump_table(
                    ins,
                    func_insns[:i_pos],
                    loaded,
                    text_sec,
                    f_start,
                    f_end,
                    rodata_refs,
                )
                if jt is not None:
                    jump_tables[ins.addr] = jt
                    new_jt_targets = [t for t in jt.targets if not covered[t - text_start]]
                    if new_jt_targets:
                        for t in new_jt_targets:
                            trace_queue.append(t)
                        _run_recursive_descent()

    return DisassemblyResult(
        instructions=instructions,
        function_starts=tuple(sorted(discovered_func_starts)),
        symbol_functions=symbol_functions,
        jump_tables=jump_tables,
    )
