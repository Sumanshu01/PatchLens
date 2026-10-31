"""Function boundary partitioning and Control-Flow Graph (CFG) recovery."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from core.arch import ArchProfile, get_arch_profile
from core.disasm import (
    _NON_RETURNING_IMPORTS,
    DisassemblyResult,
    disassemble_text,
)
from core.loader import LoadedELF, load_elf
from core.models import (
    BasicBlock,
    Binary,
    Edge,
    EdgeType,
    Function,
    Instruction,
    JumpTable,
    Symbol,
)


def build_nx_cfg(func: Function) -> nx.DiGraph[int]:
    """Construct a networkx.DiGraph representation of a Function's CFG."""
    graph: nx.DiGraph[int] = nx.DiGraph(addr=func.addr, name=func.name)
    for block in func.blocks:
        graph.add_node(block.start_addr, block=block)
    for edge in func.edges:
        graph.add_edge(edge.src, edge.dst, edge_type=edge.edge_type)
    return graph


def _trim_trailing_padding(
    insns: list[Instruction],
    profile: ArchProfile,
    branch_targets: set[int],
) -> list[Instruction]:
    """Strip trailing alignment NOPs/traps that follow an unconditional terminator."""
    trimmed = list(insns)
    while len(trimmed) > 1:
        last = trimmed[-1]
        if last.addr in branch_targets:
            break
        if profile.is_nop(last) or last.mnemonic == "int3":
            trimmed.pop()
            continue
        break
    return trimmed


def _compute_leaders(
    insns: list[Instruction],
    profile: ArchProfile,
    jump_tables: dict[int, JumpTable],
    non_ret_plt_addrs: set[int],
) -> set[int]:
    """Identify basic block leader addresses within a function's instruction stream."""
    if not insns:
        return set()

    insn_addrs = {ins.addr for ins in insns}
    f_start = insns[0].addr
    leaders: set[int] = {f_start}

    for idx, ins in enumerate(insns):
        # Address discontinuity forces a new block leader
        if idx > 0 and insns[idx - 1].end_addr != ins.addr:
            leaders.add(ins.addr)

        if profile.is_conditional_jump(ins) or profile.is_unconditional_jump(ins):
            bt = ins.branch_target
            if bt is not None and bt in insn_addrs:
                leaders.add(bt)
            if ins.end_addr in insn_addrs:
                leaders.add(ins.end_addr)

            if profile.is_indirect_jump(ins):
                jt = jump_tables.get(ins.addr)
                if jt is not None:
                    for target in jt.targets:
                        if target in insn_addrs:
                            leaders.add(target)

        elif profile.is_ret(ins) or profile.is_trap_or_halt(ins):
            if ins.end_addr in insn_addrs:
                leaders.add(ins.end_addr)

        elif profile.is_call(ins):
            ct = ins.call_target
            # Self-recursive or intra-function call target is a block leader
            if ct is not None and ct in insn_addrs:
                leaders.add(ct)
            # Non-returning call terminates the current block
            if ct is not None and ct in non_ret_plt_addrs and ins.end_addr in insn_addrs:
                leaders.add(ins.end_addr)

    return leaders


def recover_function_cfg(
    f_start: int,
    f_limit: int,
    insns_in_range: list[Instruction],
    sym: Symbol | None,
    profile: ArchProfile,
    jump_tables: dict[int, JumpTable],
    non_ret_plt_addrs: set[int],
) -> Function | None:
    """Build basic blocks and typed CFG edges for a single function."""
    if not insns_in_range or insns_in_range[0].addr != f_start:
        return None

    # Gather intra-range branch targets so trailing padding trimmer preserves jump targets
    intra_targets: set[int] = set()
    for ins in insns_in_range:
        if ins.branch_target is not None and f_start <= ins.branch_target < f_limit:
            intra_targets.add(ins.branch_target)
        jt = jump_tables.get(ins.addr)
        if jt is not None:
            for t in jt.targets:
                if f_start <= t < f_limit:
                    intra_targets.add(t)

    func_insns = _trim_trailing_padding(insns_in_range, profile, intra_targets)
    if not func_insns:
        return None

    leaders = _compute_leaders(func_insns, profile, jump_tables, non_ret_plt_addrs)
    sorted_leaders = sorted(leaders)

    # Partition instructions into contiguous basic blocks
    raw_blocks: dict[int, list[Instruction]] = {}
    curr_leader = sorted_leaders[0]
    leader_set = set(sorted_leaders)

    for ins in func_insns:
        if ins.addr in leader_set:
            curr_leader = ins.addr
            raw_blocks.setdefault(curr_leader, [])
        raw_blocks[curr_leader].append(ins)

    block_starts = set(raw_blocks.keys())
    tail_calls: list[int] = []
    call_targets: list[int] = []
    func_jump_tables: list[JumpTable] = []
    edges_by_block: dict[int, list[Edge]] = {b_start: [] for b_start in raw_blocks}

    def _add_edge(src: int, dst: int, edge_type: EdgeType) -> None:
        if dst not in block_starts:
            return
        edge = Edge(src=src, dst=dst, edge_type=edge_type)
        if edge not in edges_by_block[src]:
            edges_by_block[src].append(edge)

    for b_start, b_insns in raw_blocks.items():
        # Record direct calls inside the block
        for ins in b_insns:
            if profile.is_call(ins) and ins.call_target is not None:
                ct = ins.call_target
                if ct not in call_targets:
                    call_targets.append(ct)
                if ct in block_starts:
                    _add_edge(b_start, ct, EdgeType.CALL)

        last = b_insns[-1]

        if profile.is_ret(last) or profile.is_trap_or_halt(last):
            continue

        if profile.is_unconditional_jump(last):
            bt = last.branch_target
            if bt is not None:
                if bt in block_starts:
                    _add_edge(b_start, bt, EdgeType.JUMP)
                else:
                    # Jump outside function bounds -> tail call
                    if bt not in tail_calls:
                        tail_calls.append(bt)
                    if bt not in call_targets:
                        call_targets.append(bt)
            elif profile.is_indirect_jump(last):
                jt = jump_tables.get(last.addr)
                if jt is not None:
                    valid_targets = tuple(t for t in jt.targets if t in block_starts)
                    if valid_targets:
                        func_jump_tables.append(
                            JumpTable(
                                insn_addr=jt.insn_addr,
                                table_addr=jt.table_addr,
                                targets=valid_targets,
                            )
                        )
                        for t in valid_targets:
                            _add_edge(b_start, t, EdgeType.JUMP)
            continue

        if profile.is_conditional_jump(last):
            bt = last.branch_target
            if bt is not None:
                if bt in block_starts:
                    _add_edge(b_start, bt, EdgeType.CONDITIONAL_TRUE)
                else:
                    if bt not in tail_calls:
                        tail_calls.append(bt)
                    if bt not in call_targets:
                        call_targets.append(bt)
            if last.end_addr in block_starts:
                _add_edge(b_start, last.end_addr, EdgeType.CONDITIONAL_FALSE)
            continue

        # Standard instruction or call at end of block
        if profile.is_call(last) and last.call_target in non_ret_plt_addrs:
            continue

        if last.end_addr in block_starts:
            _add_edge(b_start, last.end_addr, EdgeType.FALLTHROUGH)

    # Build temporary DiGraph to check reachability from f_start
    temp_graph: nx.DiGraph[int] = nx.DiGraph()
    for b_start in raw_blocks:
        temp_graph.add_node(b_start)
    for b_edges in edges_by_block.values():
        for e in b_edges:
            temp_graph.add_edge(e.src, e.dst, edge_type=e.edge_type)

    reachable: set[int] = nx.descendants(temp_graph, f_start) | {f_start}

    # If the function contains a reachable indirect jump and there are unreached non-NOP
    # switch-case blocks within the function, connect them from the closest preceding indirect jump
    indirect_jump_blocks = [
        b_start
        for b_start in sorted(reachable)
        if profile.is_indirect_jump(raw_blocks[b_start][-1])
    ]
    if indirect_jump_blocks:
        unreached = sorted(block_starts - reachable)
        for ub in unreached:
            ub_insns = raw_blocks[ub]
            if all(profile.is_nop(i) or i.mnemonic == "endbr64" for i in ub_insns):
                continue
            # Pick the closest indirect jump block preceding `ub` (or the first one)
            prior_ij = [ij for ij in indirect_jump_blocks if ij < ub]
            src_ij = prior_ij[-1] if prior_ij else indirect_jump_blocks[-1]
            _add_edge(src_ij, ub, EdgeType.JUMP)
            temp_graph.add_edge(src_ij, ub, edge_type=EdgeType.JUMP)
        reachable = nx.descendants(temp_graph, f_start) | {f_start}

    # Filter to reachable blocks and edges between reachable blocks (guarantees 0 dangling edges)
    final_blocks: list[BasicBlock] = []
    final_edges: list[Edge] = []
    for b_start in sorted(reachable):
        b_insns = raw_blocks[b_start]
        b_out = tuple(e for e in edges_by_block[b_start] if e.dst in reachable)
        final_blocks.append(
            BasicBlock(
                start_addr=b_start,
                end_addr=b_insns[-1].end_addr,
                instructions=tuple(b_insns),
                out_edges=b_out,
            )
        )
        final_edges.extend(b_out)

    if not final_blocks:
        return None

    func_end = final_blocks[-1].end_addr
    func_size = sym.size if (sym is not None and sym.size > 0) else (func_end - f_start)
    func_name = sym.name if sym is not None else f"sub_{f_start:x}"
    is_symbol_backed = sym is not None

    return Function(
        addr=f_start,
        size=func_size,
        name=func_name,
        is_symbol_backed=is_symbol_backed,
        blocks=tuple(final_blocks),
        edges=tuple(final_edges),
        jump_tables=tuple(func_jump_tables),
        tail_calls=tuple(tail_calls),
        call_targets=tuple(call_targets),
    )


def recover_all_functions(
    loaded: LoadedELF,
    disasm: DisassemblyResult | None = None,
) -> tuple[Function, ...]:
    """Recover all functions and their CFGs from a LoadedELF binary."""
    if disasm is None:
        disasm = disassemble_text(loaded)

    binary = loaded.binary
    text_sec = binary.get_section(".text")
    if text_sec is None or not disasm.function_starts:
        return ()

    profile = get_arch_profile(binary.arch)
    text_end = text_sec.addr + text_sec.size
    non_ret_plt_addrs: set[int] = {
        imp.plt_addr
        for imp in binary.imports
        if imp.name in _NON_RETURNING_IMPORTS and imp.plt_addr != 0
    }

    sorted_starts = list(disasm.function_starts)
    sorted_insn_addrs = sorted(disasm.instructions.keys())
    functions: list[Function] = []

    for idx, f_start in enumerate(sorted_starts):
        next_start = sorted_starts[idx + 1] if idx + 1 < len(sorted_starts) else text_end
        sym = disasm.symbol_functions.get(f_start)
        if sym is not None and sym.size > 0:
            f_limit = min(next_start, sym.addr + sym.size)
        else:
            f_limit = next_start

        insns_in_range = [
            disasm.instructions[a] for a in sorted_insn_addrs if f_start <= a < f_limit
        ]
        func = recover_function_cfg(
            f_start=f_start,
            f_limit=f_limit,
            insns_in_range=insns_in_range,
            sym=sym,
            profile=profile,
            jump_tables=disasm.jump_tables,
            non_ret_plt_addrs=non_ret_plt_addrs,
        )
        if func is not None:
            functions.append(func)

    return tuple(functions)


def analyze_binary(path: str | Path) -> Binary:
    """Full Part 1 analysis pipeline: load ELF, disassemble .text, recover functions & CFGs."""
    loaded = load_elf(path)
    disasm = disassemble_text(loaded)
    functions = recover_all_functions(loaded, disasm)
    b = loaded.binary
    return Binary(
        path=b.path,
        sha256=b.sha256,
        arch=b.arch,
        bits=b.bits,
        endian=b.endian,
        is_pie=b.is_pie,
        is_stripped=b.is_stripped,
        entry_point=b.entry_point,
        sections=b.sections,
        symbols=b.symbols,
        imports=b.imports,
        functions=functions,
    )
