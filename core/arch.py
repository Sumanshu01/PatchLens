"""Architecture abstraction layer for PatchLens disassembly and control-flow analysis."""

from __future__ import annotations

import struct
from abc import ABC, abstractmethod

import capstone
from capstone import x86

from core.models import Architecture, Instruction


class ArchProfile(ABC):
    """Abstract base class defining architecture-specific analysis behavior."""

    @property
    @abstractmethod
    def arch(self) -> Architecture:
        """Return the Architecture enum identifier."""

    @abstractmethod
    def create_disassembler(self, endian: str = "little") -> capstone.Cs:
        """Create and configure a Capstone disassembler instance."""

    @abstractmethod
    def extract_targets(
        self, cs_insn: capstone.CsInsn
    ) -> tuple[int | None, int | None, int | None]:
        """Extract (branch_target, call_target, rip_target) from a Capstone instruction."""

    @abstractmethod
    def is_call(self, insn: Instruction) -> bool:
        """Return True if instruction is a subroutine call."""

    @abstractmethod
    def is_ret(self, insn: Instruction) -> bool:
        """Return True if instruction returns from a function."""

    @abstractmethod
    def is_unconditional_jump(self, insn: Instruction) -> bool:
        """Return True if instruction is an unconditional direct or indirect jump."""

    @abstractmethod
    def is_conditional_jump(self, insn: Instruction) -> bool:
        """Return True if instruction is a conditional branch."""

    @abstractmethod
    def is_indirect_jump(self, insn: Instruction) -> bool:
        """Return True if instruction is an indirect jump (register or memory operand)."""

    @abstractmethod
    def is_trap_or_halt(self, insn: Instruction) -> bool:
        """Return True if instruction halts execution or triggers a trap (ud2, int3, hlt)."""

    @abstractmethod
    def is_nop(self, insn: Instruction) -> bool:
        """Return True if instruction is an architectural no-op (excluding endbr64)."""

    @abstractmethod
    def padding_length(self, data: bytes, offset: int) -> int:
        """Return byte length of inter-function padding nop/trap at data[offset:], or 0."""

    @abstractmethod
    def matches_prologue(self, data: bytes, offset: int) -> bool:
        """Return True if bytes at data[offset:] match a standard function prologue."""


class X86_64Profile(ArchProfile):
    """x86-64 architecture profile."""

    _UNCOND_JUMPS = frozenset({"jmp", "jmpq", "notrack jmp", "bnd jmp"})
    _RET_MNEMONICS = frozenset({"ret", "retq", "retn", "iret", "iretq"})
    _CALL_MNEMONICS = frozenset({"call", "callq"})
    _TRAP_MNEMONICS = frozenset({"ud2", "int3", "hlt", "ud1", "ud0"})
    _NOP_MNEMONICS = frozenset({"nop", "fnop"})

    # Multi-byte NOP encodings commonly emitted by GCC/Clang for alignment
    _MULTIBYTE_NOPS: tuple[bytes, ...] = (
        b"\x66\x2e\x0f\x1f\x84\x00\x00\x00\x00\x00",  # 10-byte nop
        b"\x66\x0f\x1f\x84\x00\x00\x00\x00\x00",  # 9-byte nop
        b"\x0f\x1f\x84\x00\x00\x00\x00\x00",  # 8-byte nop
        b"\x0f\x1f\x80\x00\x00\x00\x00",  # 7-byte nop
        b"\x66\x0f\x1f\x44\x00\x00",  # 6-byte nop
        b"\x0f\x1f\x44\x00\x00",  # 5-byte nop
        b"\x0f\x1f\x40\x00",  # 4-byte nop
        b"\x0f\x1f\x00",  # 3-byte nop
        b"\x66\x90",  # 2-byte xchg ax, ax
        b"\x90",  # 1-byte nop
        b"\xcc",  # 1-byte int3 padding
    )

    @property
    def arch(self) -> Architecture:
        return Architecture.X86_64

    def create_disassembler(self, endian: str = "little") -> capstone.Cs:
        mode = capstone.CS_MODE_64
        if endian == "big":
            mode |= capstone.CS_MODE_BIG_ENDIAN
        else:
            mode |= capstone.CS_MODE_LITTLE_ENDIAN
        md = capstone.Cs(capstone.CS_ARCH_X86, mode)
        md.detail = True
        return md

    def extract_targets(
        self, cs_insn: capstone.CsInsn
    ) -> tuple[int | None, int | None, int | None]:
        mnemonic = cs_insn.mnemonic.lower()
        branch_target: int | None = None
        call_target: int | None = None
        rip_target: int | None = None

        operands = cs_insn.operands
        if operands:
            first_op = operands[0]
            if first_op.type == x86.X86_OP_IMM:
                imm_val = int(first_op.imm) & 0xFFFFFFFFFFFFFFFF
                if mnemonic in self._CALL_MNEMONICS:
                    call_target = imm_val
                elif mnemonic.startswith("j") or mnemonic in ("loop", "loope", "loopne"):
                    branch_target = imm_val

            for op in operands:
                if op.type == x86.X86_OP_MEM and op.mem.base == x86.X86_REG_RIP:
                    disp = int(op.mem.disp)
                    rip_target = (
                        int(cs_insn.address) + int(cs_insn.size) + disp
                    ) & 0xFFFFFFFFFFFFFFFF

        return branch_target, call_target, rip_target

    def is_call(self, insn: Instruction) -> bool:
        return insn.mnemonic in self._CALL_MNEMONICS or "call" in insn.groups

    def is_ret(self, insn: Instruction) -> bool:
        return insn.mnemonic in self._RET_MNEMONICS or "ret" in insn.groups

    def is_unconditional_jump(self, insn: Instruction) -> bool:
        return insn.mnemonic in self._UNCOND_JUMPS

    def is_conditional_jump(self, insn: Instruction) -> bool:
        if insn.mnemonic in self._UNCOND_JUMPS:
            return False
        if insn.mnemonic.startswith("j") or insn.mnemonic in ("loop", "loope", "loopne"):
            return True
        return "jump" in insn.groups and not self.is_unconditional_jump(insn)

    def is_indirect_jump(self, insn: Instruction) -> bool:
        return self.is_unconditional_jump(insn) and insn.branch_target is None

    def is_trap_or_halt(self, insn: Instruction) -> bool:
        return insn.mnemonic in self._TRAP_MNEMONICS

    def is_nop(self, insn: Instruction) -> bool:
        if insn.mnemonic in self._NOP_MNEMONICS:
            return True
        # Note: endbr64 is CET landing pad at function/indirect branch entry, not padding nop
        return insn.mnemonic == "xchg" and insn.op_str == "ax, ax"

    def padding_length(self, data: bytes, offset: int) -> int:
        rem = len(data) - offset
        if rem <= 0:
            return 0
        window = data[offset : offset + min(rem, 16)]
        for pat in self._MULTIBYTE_NOPS:
            if window.startswith(pat):
                return len(pat)
        # Check for repeated 0x66 prefixes followed by nop
        if window[0] == 0x66:
            idx = 0
            while idx < len(window) and window[idx] == 0x66:
                idx += 1
            for pat in self._MULTIBYTE_NOPS:
                if window[idx:].startswith(pat):
                    return idx + len(pat)
        if window[0] == 0x00 and rem >= 2 and window[1] == 0x00:
            return 2
        return 0

    def matches_prologue(self, data: bytes, offset: int) -> bool:
        rem = len(data) - offset
        if rem < 4:
            return False
        window = data[offset : offset + min(rem, 16)]

        # 1. Intel CET landing pad: endbr64 (f3 0f 1e fa) at function start
        if window.startswith(b"\xf3\x0f\x1e\xfa"):
            if len(window) <= 4:
                return False
            after = window[4:]
            # Ignore endbr64 followed immediately by padding
            return after[0] not in (0x90, 0xCC, 0x00)

        # 2. Classic frame pointer prologue: push rbp; mov rbp, rsp (55 48 89 e5)
        if window.startswith(b"\x55\x48\x89\xe5"):
            return True

        # 3. Callee-saved register push sequences:
        #    push r15/r14/r13/r12 (41 57, 41 56, 41 55, 41 54) or push rbp (55) or push rbx (53)
        #    followed by another push, mov reg, or sub rsp
        idx = 0
        push_count = 0
        while idx < len(window):
            if (
                idx + 1 < len(window)
                and window[idx] == 0x41
                and window[idx + 1] in (0x54, 0x55, 0x56, 0x57)
            ):
                push_count += 1
                idx += 2
            elif window[idx] in (0x55, 0x53):
                push_count += 1
                idx += 1
            else:
                break

        if push_count >= 2:
            return True
        if push_count == 1 and idx + 3 <= len(window):
            rest = window[idx:]
            # Followed by mov r.. or sub rsp, imm
            if rest.startswith((b"\x48\x83\xec", b"\x48\x81\xec", b"\x48\x89", b"\x49\x89")):
                return True

        # 4. Direct stack allocation at leaf-with-frame start: sub rsp, imm8/imm32
        return bool(window.startswith((b"\x48\x83\xec", b"\x48\x81\xec")))


class ARM64Profile(ArchProfile):
    """ARM64 (AArch64) architecture profile stub for cross-architecture extensibility."""

    @property
    def arch(self) -> Architecture:
        return Architecture.ARM64

    def create_disassembler(self, endian: str = "little") -> capstone.Cs:
        mode = capstone.CS_MODE_ARM
        if endian == "big":
            mode |= capstone.CS_MODE_BIG_ENDIAN
        else:
            mode |= capstone.CS_MODE_LITTLE_ENDIAN
        md = capstone.Cs(capstone.CS_ARCH_ARM64, mode)
        md.detail = True
        return md

    def extract_targets(
        self, cs_insn: capstone.CsInsn
    ) -> tuple[int | None, int | None, int | None]:
        mnemonic = cs_insn.mnemonic.lower()
        if cs_insn.operands:
            op0 = cs_insn.operands[0]
            if op0.type == capstone.arm64.ARM64_OP_IMM:
                target = int(op0.imm) & 0xFFFFFFFFFFFFFFFF
                if mnemonic == "bl":
                    return None, target, None
                if mnemonic.startswith("b") or mnemonic in ("cbz", "cbnz", "tbz", "tbnz"):
                    return target, None, None
        return None, None, None

    def is_call(self, insn: Instruction) -> bool:
        return insn.mnemonic in ("bl", "blr")

    def is_ret(self, insn: Instruction) -> bool:
        return insn.mnemonic == "ret"

    def is_unconditional_jump(self, insn: Instruction) -> bool:
        return insn.mnemonic in ("b", "br")

    def is_conditional_jump(self, insn: Instruction) -> bool:
        return insn.mnemonic.startswith("b.") or insn.mnemonic in ("cbz", "cbnz", "tbz", "tbnz")

    def is_indirect_jump(self, insn: Instruction) -> bool:
        return insn.mnemonic == "br"

    def is_trap_or_halt(self, insn: Instruction) -> bool:
        return insn.mnemonic in ("brk", "hlt", "udf")

    def is_nop(self, insn: Instruction) -> bool:
        return insn.mnemonic == "nop"

    def padding_length(self, data: bytes, offset: int) -> int:
        if offset + 4 <= len(data) and data[offset : offset + 4] == b"\x1f\x20\x03\xd5":
            return 4
        return 0

    def matches_prologue(self, data: bytes, offset: int) -> bool:
        if offset + 4 > len(data):
            return False
        word = struct.unpack_from("<I", data, offset)[0]
        # paciasp / bti c or stp x29, x30, [sp, #-imm]!
        if word in (0xD503233F, 0xD503245F):
            return True
        return bool((word & 0xFFC07FFF) == 0xA9807BFD)


def get_arch_profile(arch: Architecture) -> ArchProfile:
    """Return the ArchProfile instance for the requested architecture."""
    if arch == Architecture.X86_64:
        return X86_64Profile()
    if arch == Architecture.ARM64:
        return ARM64Profile()
    raise ValueError(f"Unsupported architecture: {arch}")
