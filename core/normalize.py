"""Instruction and function normalization for compiler-resilient binary comparison."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

from core.models import Function, Instruction

# NOP, padding, and landing pad mnemonics stripped during normalization
_IGNORED_MNEMONICS: frozenset[str] = frozenset(
    {
        "nop",
        "fnop",
        "endbr64",
        "endbr32",
        "int3",
    }
)

# Conditional jump canonicalization mapping (folding equivalent conditions)
_JCC_SYNONYMS: dict[str, str] = {
    "jz": "je",
    "jnz": "jne",
    "jc": "jb",
    "jnae": "jb",
    "jnc": "jae",
    "jnb": "jae",
    "jna": "jbe",
    "jnbe": "ja",
    "jnge": "jl",
    "jnl": "jge",
    "jng": "jle",
    "jnle": "jg",
    "jmpq": "jmp",
    "retq": "ret",
    "retn": "ret",
    "callq": "call",
}

# x86-64 register aliases to 64-bit parent register
_REG_TO_EXACT: dict[str, str] = {
    # RAX
    "rax": "rax",
    "eax": "rax",
    "ax": "rax",
    "al": "rax",
    "ah": "rax",
    # RBX
    "rbx": "rbx",
    "ebx": "rbx",
    "bx": "rbx",
    "bl": "rbx",
    "bh": "rbx",
    # RCX
    "rcx": "rcx",
    "ecx": "rcx",
    "cx": "rcx",
    "cl": "rcx",
    "ch": "rcx",
    # RDX
    "rdx": "rdx",
    "edx": "rdx",
    "dx": "rdx",
    "dl": "rdx",
    "dh": "rdx",
    # RSI
    "rsi": "rsi",
    "esi": "rsi",
    "si": "rsi",
    "sil": "rsi",
    # RDI
    "rdi": "rdi",
    "edi": "rdi",
    "di": "rdi",
    "dil": "rdi",
    # RBP
    "rbp": "rbp",
    "ebp": "rbp",
    "bp": "rbp",
    "bpl": "rbp",
    # RSP
    "rsp": "rsp",
    "esp": "rsp",
    "sp": "rsp",
    "spl": "rsp",
    # R8
    "r8": "r8",
    "r8d": "r8",
    "r8w": "r8",
    "r8b": "r8",
    # R9
    "r9": "r9",
    "r9d": "r9",
    "r9w": "r9",
    "r9b": "r9",
    # R10
    "r10": "r10",
    "r10d": "r10",
    "r10w": "r10",
    "r10b": "r10",
    # R11
    "r11": "r11",
    "r11d": "r11",
    "r11w": "r11",
    "r11b": "r11",
    # R12
    "r12": "r12",
    "r12d": "r12",
    "r12w": "r12",
    "r12b": "r12",
    # R13
    "r13": "r13",
    "r13d": "r13",
    "r13w": "r13",
    "r13b": "r13",
    # R14
    "r14": "r14",
    "r14d": "r14",
    "r14w": "r14",
    "r14b": "r14",
    # R15
    "r15": "r15",
    "r15d": "r15",
    "r15w": "r15",
    "r15b": "r15",
    # RIP
    "rip": "rip",
    "eip": "rip",
    "ip": "rip",
}

# x86-64 System V ABI functional roles
_REG_TO_ROLE: dict[str, str] = {
    # Return value
    "rax": "RET",
    "eax": "RET",
    "ax": "RET",
    "al": "RET",
    "ah": "RET",
    # Argument registers (SysV ABI: rdi, rsi, rdx, rcx, r8, r9)
    "rdi": "ARG0",
    "edi": "ARG0",
    "di": "ARG0",
    "dil": "ARG0",
    "rsi": "ARG1",
    "esi": "ARG1",
    "si": "ARG1",
    "sil": "ARG1",
    "rdx": "ARG2",
    "edx": "ARG2",
    "dx": "ARG2",
    "dl": "ARG2",
    "dh": "ARG2",
    "rcx": "ARG3",
    "ecx": "ARG3",
    "cx": "ARG3",
    "cl": "ARG3",
    "ch": "ARG3",
    "r8": "ARG4",
    "r8d": "ARG4",
    "r8w": "ARG4",
    "r8b": "ARG4",
    "r9": "ARG5",
    "r9d": "ARG5",
    "r9w": "ARG5",
    "r9b": "ARG5",
    # Callee-saved registers (SysV ABI: rbx, r12, r13, r14, r15, rbp)
    "rbx": "CALLEE",
    "ebx": "CALLEE",
    "bx": "CALLEE",
    "bl": "CALLEE",
    "bh": "CALLEE",
    "r12": "CALLEE",
    "r12d": "CALLEE",
    "r12w": "CALLEE",
    "r12b": "CALLEE",
    "r13": "CALLEE",
    "r13d": "CALLEE",
    "r13w": "CALLEE",
    "r13b": "CALLEE",
    "r14": "CALLEE",
    "r14d": "CALLEE",
    "r14w": "CALLEE",
    "r14b": "CALLEE",
    "r15": "CALLEE",
    "r15d": "CALLEE",
    "r15w": "CALLEE",
    "r15b": "CALLEE",
    # Scratch registers (r10, r11)
    "r10": "SCRATCH",
    "r10d": "SCRATCH",
    "r10w": "SCRATCH",
    "r10b": "SCRATCH",
    "r11": "SCRATCH",
    "r11d": "SCRATCH",
    "r11w": "SCRATCH",
    "r11b": "SCRATCH",
    # Stack and base pointers
    "rsp": "SP",
    "esp": "SP",
    "sp": "SP",
    "spl": "SP",
    "rbp": "FP",
    "ebp": "FP",
    "bp": "FP",
    "bpl": "FP",
    # Instruction pointer
    "rip": "IP",
    "eip": "IP",
    "ip": "IP",
}

_WORD_REGEX = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_NUM_REGEX = re.compile(r"\b(0x[0-9a-fA-F]+|-?[0-9]+)\b")


class RegisterStrategy(ABC):
    """Abstract strategy for canonicalizing register identifiers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the register normalization strategy."""

    @abstractmethod
    def canonicalize_register(self, reg: str) -> str:
        """Map a single register token to its canonical representation."""

    def canonicalize_text(self, text: str) -> str:
        """Replace all register tokens in `text` with their canonical representation."""

        def _sub(m: re.Match[str]) -> str:
            token = m.group(0)
            if (
                token.isupper()
                and len(token) > 1
                and token
                not in (
                    "RAX",
                    "RBX",
                    "RCX",
                    "RDX",
                    "RSI",
                    "RDI",
                    "RBP",
                    "RSP",
                    "RIP",
                    "EAX",
                    "EBX",
                    "ECX",
                    "EDX",
                )
            ):
                return token
            lower_word = token.lower()
            canon = self.canonicalize_register(lower_word)
            if canon.lower() != lower_word:
                return canon
            return token

        return _WORD_REGEX.sub(_sub, text)


class RoleRegisterStrategy(RegisterStrategy):
    """Canonicalize registers to their System V AMD64 ABI functional role."""

    @property
    def name(self) -> str:
        return "role"

    def canonicalize_register(self, reg: str) -> str:
        r = reg.lower()
        if r in _REG_TO_ROLE:
            return _REG_TO_ROLE[r]
        if r.startswith(("xmm", "ymm", "zmm")):
            return "VEC"
        return reg


class AbstractRegisterStrategy(RegisterStrategy):
    """Abstract all general-purpose registers to REG while preserving SP, FP, IP, VEC."""

    @property
    def name(self) -> str:
        return "abstract"

    def canonicalize_register(self, reg: str) -> str:
        r = reg.lower()
        if r in ("rsp", "esp", "sp", "spl"):
            return "SP"
        if r in ("rbp", "ebp", "bp", "bpl"):
            return "FP"
        if r in ("rip", "eip", "ip"):
            return "IP"
        if r.startswith(("xmm", "ymm", "zmm")):
            return "VEC"
        if r in _REG_TO_EXACT:
            return "REG"
        return reg


class ExactRegisterStrategy(RegisterStrategy):
    """Canonicalize register aliases to their 64-bit parent register names."""

    @property
    def name(self) -> str:
        return "exact"

    def canonicalize_register(self, reg: str) -> str:
        r = reg.lower()
        if r in _REG_TO_EXACT:
            return _REG_TO_EXACT[r].upper()
        if r.startswith(("xmm", "ymm", "zmm")):
            return r.upper()
        return reg


@dataclass(frozen=True, slots=True)
class NormalizedInstruction:
    """A single normalized, compiler-resilient machine instruction."""

    addr: int
    mnemonic: str
    op_str: str
    raw_str: str
    is_call: bool = False
    call_symbol: str | None = None
    small_constants: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedFunction:
    """A function converted into its compiler-resilient normalized form."""

    addr: int
    name: str
    instructions: tuple[NormalizedInstruction, ...]

    @property
    def token_sequence(self) -> tuple[str, ...]:
        """Sequence of normalized instruction strings."""
        return tuple(insn.raw_str for insn in self.instructions)

    @property
    def instruction_count(self) -> int:
        return len(self.instructions)


class InstructionNormalizer:
    """Converts disassembled functions and instructions into compiler-resilient representations."""

    def __init__(
        self,
        register_strategy: RegisterStrategy | None = None,
        small_imm_threshold: int = 255,
    ) -> None:
        self.register_strategy = register_strategy or RoleRegisterStrategy()
        self.small_imm_threshold = small_imm_threshold

    def is_ignored(self, insn: Instruction) -> bool:
        """Return True if the instruction is padding, NOP, or alignment noise."""
        mnem = insn.mnemonic.lower()
        if mnem in _IGNORED_MNEMONICS:
            return True
        # xchg ax, ax / xchg eax, eax
        return bool(mnem == "xchg" and insn.op_str in ("ax, ax", "eax, eax", "rax, rax"))

    def _mask_numbers_in_op_str(
        self,
        op_str: str,
        func_min_addr: int,
        func_max_addr: int,
    ) -> tuple[str, list[int]]:
        """Mask absolute addresses while preserving semantically meaningful small constants."""
        small_constants: list[int] = []

        def _replace_num(match: re.Match[str]) -> str:
            raw_val = match.group(0)
            try:
                val = int(raw_val, 0)
            except ValueError:
                return raw_val

            # Intra-function branch offset / target
            if func_min_addr <= val < func_max_addr:
                return "<TGT>"

            # Preserved small constant (e.g., small offsets, error codes, bit shifts)
            if abs(val) <= self.small_imm_threshold:
                small_constants.append(val)
                return str(val)

            # High virtual address
            if val >= 0x1000:
                return "<ADDR>"

            return "<IMM>"

        masked = _NUM_REGEX.sub(_replace_num, op_str)
        return masked, small_constants

    def _canonicalize_mnemonic(self, mnemonic: str) -> str:
        """Map synonyms to canonical mnemonics and strip prefixes/suffixes."""
        m = mnemonic.lower()
        # Strip prefixes like "notrack ", "bnd "
        if " " in m:
            m = m.split()[-1]
        return _JCC_SYNONYMS.get(m, m)

    def normalize_instruction(
        self,
        insn: Instruction,
        func_min_addr: int = 0,
        func_max_addr: int = 0xFFFFFFFFFFFFFFFF,
        import_map: Mapping[int, str] | None = None,
        func_name_map: Mapping[int, str] | None = None,
    ) -> NormalizedInstruction | None:
        """Normalize a single instruction, or return None if it should be stripped."""
        if self.is_ignored(insn):
            return None

        mnem = self._canonicalize_mnemonic(insn.mnemonic)
        op_str = insn.op_str.strip()
        call_symbol: str | None = None
        is_call = mnem == "call" or insn.call_target is not None

        # 1. Resolve call targets
        if is_call:
            target = insn.call_target
            if target is not None:
                if import_map and target in import_map:
                    call_symbol = import_map[target]
                    op_str = f"CALL_EXT:{call_symbol}"
                elif target == func_min_addr:
                    call_symbol = "CALL_SELF"
                    op_str = "CALL_SELF"
                elif func_name_map and target in func_name_map:
                    call_symbol = func_name_map[target]
                    op_str = f"CALL_SYM:{call_symbol}"
                else:
                    call_symbol = "CALL_INT"
                    op_str = "CALL_INT"
            else:
                op_str = self.register_strategy.canonicalize_text(op_str)

            raw_str = f"{mnem} {op_str}".strip()
            return NormalizedInstruction(
                addr=insn.addr,
                mnemonic=mnem,
                op_str=op_str,
                raw_str=raw_str,
                is_call=True,
                call_symbol=call_symbol,
                small_constants=(),
            )

        # 2. Canonicalize zeroing idioms: xor r, r or sub r, r -> mov <reg>, 0
        if mnem in ("xor", "sub") and "," in op_str:
            parts = [p.strip().lower() for p in op_str.split(",", 1)]
            if len(parts) == 2 and parts[0] == parts[1] and parts[0] in _REG_TO_ROLE:
                canon_reg = self.register_strategy.canonicalize_register(parts[0])
                mnem = "mov"
                op_str = f"{canon_reg}, 0"
                return NormalizedInstruction(
                    addr=insn.addr,
                    mnemonic=mnem,
                    op_str=op_str,
                    raw_str=f"{mnem} {op_str}",
                    is_call=False,
                    call_symbol=None,
                    small_constants=(0,),
                )

        # 3. Canonicalize zero-testing idioms: test r, r or or r, r -> cmp <reg>, 0
        if mnem in ("test", "or") and "," in op_str:
            parts = [p.strip().lower() for p in op_str.split(",", 1)]
            if len(parts) == 2 and parts[0] == parts[1] and parts[0] in _REG_TO_ROLE:
                canon_reg = self.register_strategy.canonicalize_register(parts[0])
                mnem = "cmp"
                op_str = f"{canon_reg}, 0"
                return NormalizedInstruction(
                    addr=insn.addr,
                    mnemonic=mnem,
                    op_str=op_str,
                    raw_str=f"{mnem} {op_str}",
                    is_call=False,
                    call_symbol=None,
                    small_constants=(0,),
                )

        # 4. Canonicalize inc/dec to add/sub 1
        if mnem == "inc":
            canon_reg = self.register_strategy.canonicalize_text(op_str)
            mnem = "add"
            op_str = f"{canon_reg}, 1"
            return NormalizedInstruction(
                addr=insn.addr,
                mnemonic=mnem,
                op_str=op_str,
                raw_str=f"{mnem} {op_str}",
                is_call=False,
                call_symbol=None,
                small_constants=(1,),
            )
        if mnem == "dec":
            canon_reg = self.register_strategy.canonicalize_text(op_str)
            mnem = "sub"
            op_str = f"{canon_reg}, 1"
            return NormalizedInstruction(
                addr=insn.addr,
                mnemonic=mnem,
                op_str=op_str,
                raw_str=f"{mnem} {op_str}",
                is_call=False,
                call_symbol=None,
                small_constants=(1,),
            )

        # 5. Canonicalize simple arithmetic LEA: lea reg, [reg + c] -> add/sub reg, c
        if mnem == "lea" and "," in op_str:
            dst_part, mem_part = [p.strip() for p in op_str.split(",", 1)]
            dst_reg = dst_part.lower()
            if mem_part.startswith("[") and mem_part.endswith("]"):
                inner = mem_part[1:-1].strip()
                # Check for simple "[dst_reg + c]" or "[dst_reg - c]"
                lea_match = re.match(
                    rf"^{dst_reg}\s*([+-])\s*(0x[0-9a-fA-F]+|[0-9]+)$",
                    inner,
                    re.IGNORECASE,
                )
                if lea_match:
                    sign = lea_match.group(1)
                    val = int(lea_match.group(2), 0)
                    canon_dst = self.register_strategy.canonicalize_register(dst_reg)
                    if sign == "+":
                        mnem = "add"
                        op_str = f"{canon_dst}, {val}"
                        return NormalizedInstruction(
                            addr=insn.addr,
                            mnemonic=mnem,
                            op_str=op_str,
                            raw_str=f"{mnem} {op_str}",
                            is_call=False,
                            call_symbol=None,
                            small_constants=(val,),
                        )
                    else:
                        mnem = "sub"
                        op_str = f"{canon_dst}, {val}"
                        return NormalizedInstruction(
                            addr=insn.addr,
                            mnemonic=mnem,
                            op_str=op_str,
                            raw_str=f"{mnem} {op_str}",
                            is_call=False,
                            call_symbol=None,
                            small_constants=(val,),
                        )

        # 6. RIP-relative memory operand canonicalization
        if "rip +" in op_str or "rip -" in op_str:
            op_str = re.sub(
                r"\[\s*rip\s*[+-]\s*(0x[0-9a-fA-F]+|[0-9]+)\s*\]",
                "[IP+MEM]",
                op_str,
                flags=re.IGNORECASE,
            )

        # 7. Mask absolute addresses & capture small constants
        masked_op_str, small_consts = self._mask_numbers_in_op_str(
            op_str, func_min_addr, func_max_addr
        )

        # 8. Canonicalize register identifiers
        canon_op_str = self.register_strategy.canonicalize_text(masked_op_str)
        raw_str = f"{mnem} {canon_op_str}".strip()

        return NormalizedInstruction(
            addr=insn.addr,
            mnemonic=mnem,
            op_str=canon_op_str,
            raw_str=raw_str,
            is_call=False,
            call_symbol=None,
            small_constants=tuple(small_consts),
        )

    def normalize_function(
        self,
        func: Function,
        import_map: Mapping[int, str] | None = None,
        func_name_map: Mapping[int, str] | None = None,
    ) -> NormalizedFunction:
        """Normalize all instructions in a function."""
        f_min = func.addr
        f_max = func.blocks[-1].end_addr if func.blocks else (func.addr + func.size)
        norm_insns: list[NormalizedInstruction] = []

        for block in func.blocks:
            for insn in block.instructions:
                norm = self.normalize_instruction(
                    insn,
                    func_min_addr=f_min,
                    func_max_addr=f_max,
                    import_map=import_map,
                    func_name_map=func_name_map,
                )
                if norm is not None:
                    norm_insns.append(norm)

        return NormalizedFunction(
            addr=func.addr,
            name=func.name,
            instructions=tuple(norm_insns),
        )
