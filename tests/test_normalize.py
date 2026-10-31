"""Unit tests for core/normalize.py instruction normalization and register strategies."""

from __future__ import annotations

from core.models import Instruction
from core.normalize import (
    AbstractRegisterStrategy,
    ExactRegisterStrategy,
    InstructionNormalizer,
    RoleRegisterStrategy,
)


def _make_insn(
    addr: int,
    mnemonic: str,
    op_str: str,
    call_target: int | None = None,
    branch_target: int | None = None,
    rip_target: int | None = None,
) -> Instruction:
    return Instruction(
        addr=addr,
        size=4,
        mnemonic=mnemonic,
        op_str=op_str,
        raw_bytes=b"\x90\x90\x90\x90",
        branch_target=branch_target,
        call_target=call_target,
        rip_target=rip_target,
    )


def test_ignored_instructions_stripped() -> None:
    norm = InstructionNormalizer()
    for mnem in ("nop", "fnop", "endbr64", "endbr32", "int3"):
        insn = _make_insn(0x1000, mnem, "")
        assert norm.normalize_instruction(insn) is None

    # Multi-byte nop xchg ax, ax
    xchg_insn = _make_insn(0x1000, "xchg", "ax, ax")
    assert norm.normalize_instruction(xchg_insn) is None


def test_register_strategies() -> None:
    role_strat = RoleRegisterStrategy()
    assert role_strat.canonicalize_register("rax") == "RET"
    assert role_strat.canonicalize_register("eax") == "RET"
    assert role_strat.canonicalize_register("rdi") == "ARG0"
    assert role_strat.canonicalize_register("rsi") == "ARG1"
    assert role_strat.canonicalize_register("rbx") == "CALLEE"
    assert role_strat.canonicalize_register("r12") == "CALLEE"
    assert role_strat.canonicalize_register("r10") == "SCRATCH"
    assert role_strat.canonicalize_register("rsp") == "SP"
    assert role_strat.canonicalize_register("rbp") == "FP"
    assert role_strat.canonicalize_register("rip") == "IP"
    assert role_strat.canonicalize_register("xmm0") == "VEC"

    abstract_strat = AbstractRegisterStrategy()
    assert abstract_strat.canonicalize_register("rax") == "REG"
    assert abstract_strat.canonicalize_register("rdi") == "REG"
    assert abstract_strat.canonicalize_register("rsp") == "SP"
    assert abstract_strat.canonicalize_register("rbp") == "FP"
    assert abstract_strat.canonicalize_register("rip") == "IP"
    assert abstract_strat.canonicalize_register("ymm1") == "VEC"

    exact_strat = ExactRegisterStrategy()
    assert exact_strat.canonicalize_register("eax") == "RAX"
    assert exact_strat.canonicalize_register("edi") == "RDI"
    assert exact_strat.canonicalize_register("r12d") == "R12"


def test_zeroing_idioms_canonicalization() -> None:
    norm = InstructionNormalizer(register_strategy=RoleRegisterStrategy())

    insn_xor = _make_insn(0x1000, "xor", "eax, eax")
    res_xor = norm.normalize_instruction(insn_xor)
    assert res_xor is not None
    assert res_xor.mnemonic == "mov"
    assert res_xor.op_str == "RET, 0"

    insn_sub = _make_insn(0x1004, "sub", "rdi, rdi")
    res_sub = norm.normalize_instruction(insn_sub)
    assert res_sub is not None
    assert res_sub.mnemonic == "mov"
    assert res_sub.op_str == "ARG0, 0"


def test_zero_testing_idioms_canonicalization() -> None:
    norm = InstructionNormalizer(register_strategy=RoleRegisterStrategy())

    insn_test = _make_insn(0x1000, "test", "rsi, rsi")
    res_test = norm.normalize_instruction(insn_test)
    assert res_test is not None
    assert res_test.mnemonic == "cmp"
    assert res_test.op_str == "ARG1, 0"

    insn_or = _make_insn(0x1004, "or", "edx, edx")
    res_or = norm.normalize_instruction(insn_or)
    assert res_or is not None
    assert res_or.mnemonic == "cmp"
    assert res_or.op_str == "ARG2, 0"


def test_inc_dec_canonicalization() -> None:
    norm = InstructionNormalizer(register_strategy=RoleRegisterStrategy())

    insn_inc = _make_insn(0x1000, "inc", "rax")
    res_inc = norm.normalize_instruction(insn_inc)
    assert res_inc is not None
    assert res_inc.mnemonic == "add"
    assert res_inc.op_str == "RET, 1"

    insn_dec = _make_insn(0x1004, "dec", "rcx")
    res_dec = norm.normalize_instruction(insn_dec)
    assert res_dec is not None
    assert res_dec.mnemonic == "sub"
    assert res_dec.op_str == "ARG3, 1"


def test_arithmetic_lea_canonicalization() -> None:
    norm = InstructionNormalizer(register_strategy=RoleRegisterStrategy())

    insn_lea_add = _make_insn(0x1000, "lea", "rax, [rax + 8]")
    res_add = norm.normalize_instruction(insn_lea_add)
    assert res_add is not None
    assert res_add.mnemonic == "add"
    assert res_add.op_str == "RET, 8"

    insn_lea_sub = _make_insn(0x1004, "lea", "rdi, [rdi - 16]")
    res_sub = norm.normalize_instruction(insn_lea_sub)
    assert res_sub is not None
    assert res_sub.mnemonic == "sub"
    assert res_sub.op_str == "ARG0, 16"


def test_jcc_synonyms_canonicalization() -> None:
    norm = InstructionNormalizer(register_strategy=RoleRegisterStrategy())

    assert norm.normalize_instruction(_make_insn(0x1000, "jz", "0x1010")).mnemonic == "je"
    assert norm.normalize_instruction(_make_insn(0x1004, "jnz", "0x1010")).mnemonic == "jne"
    assert norm.normalize_instruction(_make_insn(0x1008, "jc", "0x1010")).mnemonic == "jb"
    assert norm.normalize_instruction(_make_insn(0x100C, "jnc", "0x1010")).mnemonic == "jae"
    assert norm.normalize_instruction(_make_insn(0x1010, "jmpq", "0x1050")).mnemonic == "jmp"
    assert norm.normalize_instruction(_make_insn(0x1014, "notrack jmp", "rax")).mnemonic == "jmp"


def test_immediates_and_address_masking() -> None:
    norm = InstructionNormalizer(small_imm_threshold=255)

    # Small constant preserved
    insn_small = _make_insn(0x1000, "mov", "eax, 42")
    res_small = norm.normalize_instruction(insn_small, func_min_addr=0x1000, func_max_addr=0x1100)
    assert res_small is not None
    assert "42" in res_small.op_str
    assert res_small.small_constants == (42,)

    # Large immediate masked as <IMM> or <ADDR>
    insn_large = _make_insn(0x1004, "mov", "eax, 0x123456")
    res_large = norm.normalize_instruction(insn_large, func_min_addr=0x1000, func_max_addr=0x1100)
    assert res_large is not None
    assert "<ADDR>" in res_large.op_str

    # Intra-function target masked as <TGT>
    insn_tgt = _make_insn(0x1008, "jmp", "0x1050", branch_target=0x1050)
    res_tgt = norm.normalize_instruction(insn_tgt, func_min_addr=0x1000, func_max_addr=0x1100)
    assert res_tgt is not None
    assert "<TGT>" in res_tgt.op_str

    # RIP-relative memory operand masked
    insn_rip = _make_insn(0x100C, "lea", "rax, [rip + 0x2050]", rip_target=0x3060)
    res_rip = norm.normalize_instruction(insn_rip, func_min_addr=0x1000, func_max_addr=0x1100)
    assert res_rip is not None
    assert "[IP+MEM]" in res_rip.op_str


def test_call_target_symbolic_resolution() -> None:
    norm = InstructionNormalizer()
    import_map = {0x2000: "malloc", 0x2010: "free"}
    sym_map = {0x3000: "helper_func"}

    # External import call
    insn_ext = _make_insn(0x1000, "call", "0x2000", call_target=0x2000)
    res_ext = norm.normalize_instruction(insn_ext, import_map=import_map)
    assert res_ext is not None
    assert res_ext.call_symbol == "malloc"
    assert "CALL_EXT:malloc" in res_ext.op_str

    # Recursive call to self
    insn_self = _make_insn(0x1004, "call", "0x1000", call_target=0x1000)
    res_self = norm.normalize_instruction(insn_self, func_min_addr=0x1000)
    assert res_self is not None
    assert res_self.call_symbol == "CALL_SELF"
    assert "CALL_SELF" in res_self.op_str

    # Known internal symbol
    insn_sym = _make_insn(0x1008, "call", "0x3000", call_target=0x3000)
    res_sym = norm.normalize_instruction(insn_sym, func_name_map=sym_map)
    assert res_sym is not None
    assert res_sym.call_symbol == "helper_func"
    assert "CALL_SYM:helper_func" in res_sym.op_str

    # Unknown internal function
    insn_int = _make_insn(0x100C, "call", "0x4000", call_target=0x4000)
    res_int = norm.normalize_instruction(insn_int)
    assert res_int is not None
    assert res_int.call_symbol == "CALL_INT"
    assert "CALL_INT" in res_int.op_str
