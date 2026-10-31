"""Tests for core/cfg.py: reachability, zero dangling edges, and objdump block parity."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import networkx as nx
from core.arch import X86_64Profile
from core.cfg import analyze_binary, build_nx_cfg, recover_function_cfg
from core.models import EdgeType, Instruction


def _to_wsl_path(win_path: Path) -> str:
    resolved = win_path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", 1)[-1].lstrip("/")
    return f"/mnt/{drive}/{tail}"


def _objdump_basic_blocks(
    binary_path: Path,
    start_addr: int,
    stop_addr: int,
) -> list[tuple[int, int]]:
    """Run objdump -d on [start_addr, stop_addr) and compute ground-truth basic block ranges."""
    target_arg = _to_wsl_path(binary_path) if os.name == "nt" else str(binary_path)
    cmd = (
        f"objdump -d --no-show-raw-insn "
        f"--start-address=0x{start_addr:x} --stop-address=0x{stop_addr:x} '{target_arg}'"
    )
    if os.name == "nt":
        out = subprocess.run(
            ["wsl", "bash", "-c", cmd],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    else:
        out = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    line_re = re.compile(r"^\s*([0-9a-fA-F]+):\s+([a-zA-Z0-9_.]+)(?:\s+(.*))?$")
    target_re = re.compile(r"\b([0-9a-fA-F]{4,16})\s*<")

    insns: list[tuple[int, str, int | None]] = []
    for line in out.splitlines():
        m = line_re.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        mnemonic = m.group(2).lower()
        ops = (m.group(3) or "").strip()
        target: int | None = None
        if mnemonic.startswith("j") and not mnemonic.startswith("jmpq*"):
            tm = target_re.search(ops)
            if tm:
                target = int(tm.group(1), 16)
        insns.append((addr, mnemonic, target))

    # Trim trailing NOPs after last ret/jmp just like objdump function body
    while len(insns) > 1 and insns[-1][1] in ("nop", "xchg", "int3"):
        insns.pop()

    insn_addrs = {a for a, _, _ in insns}
    leaders: set[int] = {start_addr}
    for idx, (_addr, mnem, target) in enumerate(insns):
        is_branch = mnem.startswith("j")
        is_ret = mnem in ("ret", "retq", "ud2", "hlt")
        is_nonret_call = mnem in ("call", "callq") and "__stack_chk_fail" in out.splitlines()[idx]
        if is_branch:
            if target is not None and target in insn_addrs:
                leaders.add(target)
            if idx + 1 < len(insns):
                leaders.add(insns[idx + 1][0])
        elif (is_ret or is_nonret_call) and idx + 1 < len(insns):
            leaders.add(insns[idx + 1][0])

    sorted_leaders = sorted(leaders)
    leader_set = set(sorted_leaders)
    blocks: list[tuple[int, int]] = []
    for idx, l_start in enumerate(sorted_leaders):
        next_leader = sorted_leaders[idx + 1] if idx + 1 < len(sorted_leaders) else stop_addr
        b_insns = [i for i in insns if l_start <= i[0] < next_leader]
        if not b_insns:
            continue
        # End address of last instruction in block: either next instruction's start or stop_addr
        last_addr = b_insns[-1][0]
        last_global_idx = next(i for i, item in enumerate(insns) if item[0] == last_addr)
        b_end = insns[last_global_idx + 1][0] if last_global_idx + 1 < len(insns) else stop_addr
        blocks.append((l_start, b_end))
        _ = leader_set
    return blocks


def test_cfg_reachability_and_no_dangling_edges(
    zlib_1211_gcc_o2_unstripped: Path,
    zlib_1211_gcc_o2_stripped: Path,
) -> None:
    for path in (zlib_1211_gcc_o2_unstripped, zlib_1211_gcc_o2_stripped):
        binary = analyze_binary(path)
        assert len(binary.functions) > 80

        for func in binary.functions:
            assert func.block_count >= 1
            block_starts = {b.start_addr for b in func.blocks}
            assert func.addr in block_starts

            # 1. Zero dangling edges
            for edge in func.edges:
                assert edge.src in block_starts, (
                    f"{func.name}: edge src 0x{edge.src:x} not in blocks"
                )
                assert edge.dst in block_starts, (
                    f"{func.name}: dangling edge dst 0x{edge.dst:x} not in blocks"
                )

            # 2. Every block reachable from function entry
            graph = build_nx_cfg(func)
            reachable = nx.descendants(graph, func.addr) | {func.addr}
            assert reachable == block_starts, (
                f"{func.name} (0x{func.addr:x}): unreachable blocks "
                f"{[hex(a) for a in sorted(block_starts - reachable)]}"
            )


def test_cfg_block_boundaries_match_objdump_on_3_handpicked_functions(
    zlib_1212_gcc_o0_unstripped: Path,
) -> None:
    binary = analyze_binary(zlib_1212_gcc_o0_unstripped)
    handpicked = ("adler32", "compress2", "_tr_flush_block")

    for func_name in handpicked:
        func = binary.get_function(func_name)
        assert func is not None, f"Function {func_name} not found"
        stop_addr = func.blocks[-1].end_addr

        expected_ranges = _objdump_basic_blocks(
            zlib_1212_gcc_o0_unstripped,
            func.addr,
            stop_addr,
        )
        actual_ranges = [(b.start_addr, b.end_addr) for b in func.blocks]
        assert actual_ranges == expected_ranges, (
            f"Block boundary mismatch on {func_name}:\n"
            f"  PatchLens: {[(hex(s), hex(e)) for s, e in actual_ranges]}\n"
            f"  objdump:   {[(hex(s), hex(e)) for s, e in expected_ranges]}"
        )


def test_cfg_recursive_call_and_tail_call_edges() -> None:
    profile = X86_64Profile()
    insns = [
        Instruction(
            addr=0x2000,
            size=4,
            mnemonic="endbr64",
            op_str="",
            raw_bytes=b"\xf3\x0f\x1e\xfa",
        ),
        Instruction(
            addr=0x2004,
            size=5,
            mnemonic="call",
            op_str="0x2000",
            raw_bytes=b"\xe8\xf7\xff\xff\xff",
            groups=("call",),
            call_target=0x2000,
        ),
        Instruction(
            addr=0x2009,
            size=5,
            mnemonic="jmp",
            op_str="0x3000",
            raw_bytes=b"\xe9\xf2\x0f\x00\x00",
            groups=("jump",),
            branch_target=0x3000,
        ),
    ]
    func = recover_function_cfg(
        f_start=0x2000,
        f_limit=0x2010,
        insns_in_range=insns,
        sym=None,
        profile=profile,
        jump_tables={},
        non_ret_plt_addrs=set(),
    )
    assert func is not None
    assert func.name == "sub_2000"
    assert func.tail_calls == (0x3000,)
    assert any(e.edge_type == EdgeType.CALL and e.dst == 0x2000 for e in func.edges)
