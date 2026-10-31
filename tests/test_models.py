"""Unit tests for core/models.py immutability and JSON serialization."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from core.models import (
    Architecture,
    BasicBlock,
    Binary,
    Edge,
    EdgeType,
    Function,
    ImportEntry,
    Instruction,
    JumpTable,
    Section,
    Symbol,
)


def _sample_binary() -> Binary:
    insn1 = Instruction(
        addr=0x1000,
        size=4,
        mnemonic="endbr64",
        op_str="",
        raw_bytes=b"\xf3\x0f\x1e\xfa",
        groups=(),
    )
    insn2 = Instruction(
        addr=0x1004,
        size=2,
        mnemonic="je",
        op_str="0x100a",
        raw_bytes=b"\x74\x04",
        groups=("jump",),
        branch_target=0x100A,
    )
    insn3 = Instruction(
        addr=0x1006,
        size=4,
        mnemonic="xor",
        op_str="eax, eax",
        raw_bytes=b"\x31\xc0\x90\x90",
    )
    insn4 = Instruction(
        addr=0x100A,
        size=1,
        mnemonic="ret",
        op_str="",
        raw_bytes=b"\xc3",
        groups=("ret",),
    )

    e_true = Edge(src=0x1000, dst=0x100A, edge_type=EdgeType.CONDITIONAL_TRUE)
    e_false = Edge(src=0x1000, dst=0x1006, edge_type=EdgeType.CONDITIONAL_FALSE)
    e_fall = Edge(src=0x1006, dst=0x100A, edge_type=EdgeType.FALLTHROUGH)

    bb1 = BasicBlock(
        start_addr=0x1000,
        end_addr=0x1006,
        instructions=(insn1, insn2),
        out_edges=(e_true, e_false),
    )
    bb2 = BasicBlock(
        start_addr=0x1006,
        end_addr=0x100A,
        instructions=(insn3,),
        out_edges=(e_fall,),
    )
    bb3 = BasicBlock(
        start_addr=0x100A,
        end_addr=0x100B,
        instructions=(insn4,),
        out_edges=(),
    )

    jt = JumpTable(insn_addr=0x1004, table_addr=0x2000, targets=(0x1006, 0x100A))
    func = Function(
        addr=0x1000,
        size=11,
        name="sample_func",
        is_symbol_backed=True,
        blocks=(bb1, bb2, bb3),
        edges=(e_true, e_false, e_fall),
        jump_tables=(jt,),
        tail_calls=(0x1050,),
        call_targets=(0x1050,),
    )

    sec = Section(
        name=".text",
        addr=0x1000,
        size=0x100,
        offset=0x1000,
        flags=0x6,
        is_exec=True,
    )
    sym = Symbol(
        name="sample_func",
        addr=0x1000,
        size=11,
        binding="STB_GLOBAL",
        sym_type="STT_FUNC",
        section_name=".text",
        is_dynamic=False,
    )
    imp = ImportEntry(
        name="malloc",
        plt_addr=0x1020,
        got_addr=0x4000,
        reloc_type="7",
    )

    return Binary(
        path="/tmp/sample.so",
        sha256="a" * 64,
        arch=Architecture.X86_64,
        bits=64,
        endian="little",
        is_pie=True,
        is_stripped=False,
        entry_point=0x1000,
        sections=(sec,),
        symbols=(sym,),
        imports=(imp,),
        functions=(func,),
    )


def test_models_immutability() -> None:
    binary = _sample_binary()
    func = binary.functions[0]
    bb = func.blocks[0]
    insn = bb.instructions[0]

    with pytest.raises(FrozenInstanceError):
        binary.path = "/tmp/other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        func.name = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        bb.start_addr = 0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        insn.mnemonic = "nop"  # type: ignore[misc]


def test_models_json_roundtrip() -> None:
    binary = _sample_binary()
    raw_json = binary.to_json(indent=2)
    restored = Binary.from_json(raw_json)
    assert restored == binary

    func = binary.functions[0]
    assert Function.from_json(func.to_json()) == func
    assert func.block_count == 3
    assert func.edge_count == 3
    assert func.instruction_count == 4

    bb = func.blocks[0]
    assert BasicBlock.from_json(bb.to_json()) == bb
    assert bb.size == 6
    assert bb.instruction_count == 2

    insn = bb.instructions[0]
    assert Instruction.from_json(insn.to_json()) == insn
    assert insn.end_addr == 0x1004


def test_binary_lookup_helpers() -> None:
    binary = _sample_binary()
    sec = binary.get_section(".text")
    assert sec is not None
    assert sec.contains(0x1004)
    assert not sec.contains(0x2000)
    assert binary.get_section(".nonexistent") is None

    assert binary.get_function("sample_func") is not None
    assert binary.get_function(0x1000) is not None
    assert binary.get_function("missing") is None
    assert binary.get_function(0x9999) is None
