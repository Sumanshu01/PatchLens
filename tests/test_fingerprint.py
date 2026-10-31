"""Unit tests for core/fingerprint.py fingerprint functions and metrics."""

from __future__ import annotations

from core.fingerprint import (
    compute_callee_set,
    compute_cfg_metrics,
    compute_constants_and_strings,
    compute_md_index,
    compute_mnemonic_histogram,
    compute_normalized_hash,
    compute_token_ngrams,
    compute_wl_cfg_hash,
    extract_fingerprints,
    md_index_similarity,
    mnemonic_cosine_similarity,
    ngram_jaccard_similarity,
    wl_subtree_kernel_similarity,
)
from core.models import BasicBlock, Edge, EdgeType, Function, Instruction
from core.normalize import NormalizedFunction, NormalizedInstruction


def _make_dummy_function() -> Function:
    insn1 = Instruction(
        addr=0x1000,
        size=4,
        mnemonic="mov",
        op_str="eax, 0x10",
        raw_bytes=b"\xb8\x10\x00\x00\x00",
    )
    insn2 = Instruction(
        addr=0x1004,
        size=2,
        mnemonic="je",
        op_str="0x1010",
        raw_bytes=b"\x74\x0a",
        branch_target=0x1010,
    )
    insn3 = Instruction(
        addr=0x1006,
        size=4,
        mnemonic="add",
        op_str="eax, 1",
        raw_bytes=b"\x83\xc0\x01",
    )
    insn4 = Instruction(
        addr=0x1010,
        size=1,
        mnemonic="ret",
        op_str="",
        raw_bytes=b"\xc3",
    )

    e1 = Edge(src=0x1000, dst=0x1010, edge_type=EdgeType.CONDITIONAL_TRUE)
    e2 = Edge(src=0x1000, dst=0x1006, edge_type=EdgeType.CONDITIONAL_FALSE)
    e3 = Edge(src=0x1006, dst=0x1010, edge_type=EdgeType.FALLTHROUGH)

    bb1 = BasicBlock(
        start_addr=0x1000, end_addr=0x1006, instructions=(insn1, insn2), out_edges=(e1, e2)
    )
    bb2 = BasicBlock(start_addr=0x1006, end_addr=0x1010, instructions=(insn3,), out_edges=(e3,))
    bb3 = BasicBlock(start_addr=0x1010, end_addr=0x1011, instructions=(insn4,), out_edges=())

    return Function(
        addr=0x1000,
        size=17,
        name="test_func",
        is_symbol_backed=True,
        blocks=(bb1, bb2, bb3),
        edges=(e1, e2, e3),
        jump_tables=(),
        tail_calls=(),
        call_targets=(0x2000,),
    )


def test_normalized_hash_and_ngrams() -> None:
    tokens = ("mov RET, 16", "cmp ARG0, 0", "je <TGT>", "ret")
    h1 = compute_normalized_hash(tokens)
    assert len(h1) == 64
    assert h1 == compute_normalized_hash(tokens)

    h_empty = compute_normalized_hash(())
    assert len(h_empty) == 64

    ng1 = compute_token_ngrams(tokens, n=2)
    assert len(ng1) == 3
    assert ngram_jaccard_similarity(ng1, ng1) == 1.0
    assert ngram_jaccard_similarity(ng1, {}) == 0.0


def test_mnemonic_histogram_and_cosine() -> None:
    norm_insns = (
        NormalizedInstruction(addr=0x1000, mnemonic="mov", op_str="RET, 0", raw_str="mov RET, 0"),
        NormalizedInstruction(addr=0x1004, mnemonic="add", op_str="RET, 1", raw_str="add RET, 1"),
        NormalizedInstruction(
            addr=0x1008, mnemonic="mov", op_str="ARG0, RET", raw_str="mov ARG0, RET"
        ),
    )
    hist1 = compute_mnemonic_histogram(norm_insns)
    assert hist1 == {"mov": 2, "add": 1}

    hist2 = {"mov": 4, "add": 2}
    # Identical proportions yield cosine similarity 1.0
    assert abs(mnemonic_cosine_similarity(hist1, hist2) - 1.0) < 1e-6

    hist3 = {"sub": 2, "xor": 1}
    assert mnemonic_cosine_similarity(hist1, hist3) == 0.0


def test_wl_cfg_hash_and_kernel_similarity() -> None:
    func1 = _make_dummy_function()
    h1, subtrees1 = compute_wl_cfg_hash(func1)
    assert len(h1) == 64
    assert len(subtrees1) > 0

    # Self similarity is 1.0
    assert abs(wl_subtree_kernel_similarity(subtrees1, subtrees1) - 1.0) < 1e-6

    # Empty graph
    empty_func = Function(
        addr=0x2000,
        size=0,
        name="empty",
        is_symbol_backed=False,
        blocks=(),
        edges=(),
    )
    h_emp, subtrees_emp = compute_wl_cfg_hash(empty_func)
    assert len(h_emp) == 64
    assert wl_subtree_kernel_similarity(subtrees1, subtrees_emp) == 0.0


def test_md_index_and_similarity() -> None:
    func = _make_dummy_function()
    md1 = compute_md_index(func)
    assert md1 > 0.0

    assert md_index_similarity(md1, md1) == 1.0
    assert md_index_similarity(md1, md1 * 1.05) > 0.90
    assert md_index_similarity(0.0, 0.0) == 1.0

    single_block_func = Function(
        addr=0x3000,
        size=1,
        name="leaf",
        is_symbol_backed=False,
        blocks=(BasicBlock(0x3000, 0x3001, (Instruction(0x3000, 1, "ret", "", b"\xc3"),), ()),),
        edges=(),
    )
    assert compute_md_index(single_block_func) == 0.0


def test_cfg_metrics() -> None:
    func = _make_dummy_function()
    b_cnt, e_cnt, cc = compute_cfg_metrics(func)
    assert b_cnt == 3
    assert e_cnt == 3
    # M = E - V + 2 = 3 - 3 + 2 = 2
    assert cc == 2


def test_callee_set_and_constants() -> None:
    func = _make_dummy_function()
    import_map = {0x2000: "malloc"}
    callees = compute_callee_set(func, import_map=import_map)
    assert callees == frozenset({"malloc"})

    consts, strings = compute_constants_and_strings(func, loaded=None)
    assert isinstance(consts, frozenset)
    assert isinstance(strings, frozenset)


def test_extract_fingerprints() -> None:
    func = _make_dummy_function()
    norm_insns = (
        NormalizedInstruction(addr=0x1000, mnemonic="mov", op_str="RET, 16", raw_str="mov RET, 16"),
        NormalizedInstruction(addr=0x1004, mnemonic="je", op_str="<TGT>", raw_str="je <TGT>"),
        NormalizedInstruction(addr=0x1006, mnemonic="add", op_str="RET, 1", raw_str="add RET, 1"),
        NormalizedInstruction(addr=0x1010, mnemonic="ret", op_str="", raw_str="ret"),
    )
    norm_func = NormalizedFunction(addr=func.addr, name=func.name, instructions=norm_insns)
    fp = extract_fingerprints(func, norm_func, import_map={0x2000: "malloc"})
    assert fp.func_addr == func.addr
    assert fp.block_count == 3
    assert fp.edge_count == 3
    assert fp.cyclomatic_complexity == 2
    assert fp.callees == frozenset({"malloc"})
    assert fp.md_index > 0.0
