"""Unit tests for core/match.py multi-pass matching engine."""

from __future__ import annotations

from core.match import FunctionMatcher
from core.models import Architecture, BasicBlock, Binary, Function, Instruction


def _create_mock_binary(
    funcs: tuple[Function, ...],
    path: str = "/tmp/bin.so",
) -> Binary:
    return Binary(
        path=path,
        sha256="0" * 64,
        arch=Architecture.X86_64,
        bits=64,
        endian="little",
        is_pie=True,
        is_stripped=True,
        entry_point=funcs[0].addr if funcs else 0,
        sections=(),
        symbols=(),
        imports=(),
        functions=funcs,
    )


def _simple_func(
    addr: int,
    name: str,
    mnemonics: tuple[str, ...],
    callees: tuple[int, ...] = (),
) -> Function:
    insns = []
    curr = addr
    for m in mnemonics:
        insns.append(
            Instruction(
                addr=curr,
                size=4,
                mnemonic=m,
                op_str="",
                raw_bytes=b"\x90\x90\x90\x90",
            )
        )
        curr += 4
    bb = BasicBlock(addr, curr, tuple(insns), ())
    return Function(
        addr=addr,
        size=curr - addr,
        name=name,
        is_symbol_backed=True,
        blocks=(bb,),
        edges=(),
        call_targets=callees,
    )


def test_pass0_symbol_exact() -> None:
    f1 = _simple_func(0x1000, "target_func", ("mov", "ret"))
    f2 = _simple_func(0x2000, "target_func", ("xor", "ret"))
    bin_a = _create_mock_binary((f1,))
    bin_b = _create_mock_binary((f2,))

    matcher = FunctionMatcher(enabled_passes=["pass0_symbol_exact"])
    res = matcher.match(bin_a, bin_b, use_symbols=True)
    assert len(res.matches) == 1
    m = res.matches[0]
    assert m.pass_name == "pass0_symbol_exact"
    assert m.addr_a == 0x1000
    assert m.addr_b == 0x2000
    assert m.confidence == 1.0


def test_pass1_normalized_exact() -> None:
    f1 = _simple_func(0x1000, "sub_1000", ("mov", "add", "ret"))
    f2 = _simple_func(0x2000, "sub_2000", ("mov", "add", "ret"))
    bin_a = _create_mock_binary((f1,))
    bin_b = _create_mock_binary((f2,))

    matcher = FunctionMatcher(enabled_passes=["pass1_normalized_exact"])
    res = matcher.match(bin_a, bin_b, use_symbols=False)
    assert len(res.matches) == 1
    m = res.matches[0]
    assert m.pass_name == "pass1_normalized_exact"
    assert m.addr_a == 0x1000
    assert m.addr_b == 0x2000
    assert m.confidence >= 0.98


def test_pass4_callgraph_propagation() -> None:
    # Anchor functions match in Pass 1
    caller_a = _simple_func(0x1000, "sub_1000", ("mov", "add", "sub", "ret"), callees=(0x1100,))
    caller_b = _simple_func(0x2000, "sub_2000", ("mov", "add", "sub", "ret"), callees=(0x2100,))

    # Callee functions differ in instructions (Pass 1 fails), but call graph propagates
    callee_a = _simple_func(0x1100, "sub_1100", ("push", "pop", "ret"))
    callee_b = _simple_func(0x2100, "sub_2100", ("push", "pop", "ret"))

    bin_a = _create_mock_binary((caller_a, callee_a))
    bin_b = _create_mock_binary((caller_b, callee_b))

    matcher = FunctionMatcher(
        enabled_passes=["pass1_normalized_exact", "pass4_callgraph_propagation"]
    )
    res = matcher.match(bin_a, bin_b, use_symbols=False)
    assert len(res.matches) == 2
    matched_addrs = {(m.addr_a, m.addr_b): m.pass_name for m in res.matches}
    assert (0x1000, 0x2000) in matched_addrs
    assert (0x1100, 0x2100) in matched_addrs
    assert res.total_matches == 2


def test_unmatched_functions_reported_added_and_removed() -> None:
    f_shared_a = _simple_func(0x1000, "sub_1000", ("mov", "ret"))
    f_removed_a = _simple_func(0x1100, "sub_1100", ("nop", "ret"))

    f_shared_b = _simple_func(0x2000, "sub_2000", ("mov", "ret"))
    f_added_b = _simple_func(0x2200, "sub_2200", ("xor", "add", "sub", "ret"))

    bin_a = _create_mock_binary((f_shared_a, f_removed_a))
    bin_b = _create_mock_binary((f_shared_b, f_added_b))

    matcher = FunctionMatcher(
        enabled_passes=["pass1_normalized_exact", "pass5_global_hungarian"],
        hungarian_threshold=0.85,  # High threshold rejects dissimilar added/removed funcs
    )
    res = matcher.match(bin_a, bin_b, use_symbols=False)
    assert len(res.matches) == 1
    assert res.matches[0].addr_a == 0x1000
    assert res.matches[0].addr_b == 0x2000
    assert res.removed_count == 1
    assert res.unmatched_a == (0x1100,)
    assert res.added_count == 1
    assert res.unmatched_b == (0x2200,)
