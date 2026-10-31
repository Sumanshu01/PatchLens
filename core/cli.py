"""Command-line interface for PatchLens (inspect, diff, and eval)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from core.cfg import analyze_binary
from core.diff import diff_matched_functions
from core.eval import run_full_evaluation
from core.match import FunctionMatcher
from core.models import Binary
from core.rank import score_and_rank_diffs


def format_inspection_report(binary: Binary, function_filter: str | None = None) -> str:
    """Format a human-readable inspection summary of recovered functions, blocks, and edges."""
    funcs = list(binary.functions)
    if function_filter:
        flt = function_filter.lower()
        funcs = [
            f
            for f in funcs
            if flt in f.name.lower() or flt == f"0x{f.addr:x}" or flt == str(f.addr)
        ]

    total_blocks = sum(f.block_count for f in funcs)
    total_edges = sum(f.edge_count for f in funcs)
    edge_counts: Counter[str] = Counter()
    for f in funcs:
        for e in f.edges:
            edge_counts[e.edge_type.value] += 1

    lines: list[str] = [
        f"Binary:      {binary.path}",
        f"SHA-256:     {binary.sha256}",
        f"Arch:        {binary.arch.value} ({binary.bits}-bit, {binary.endian}-endian)",
        f"Type:        {'PIE/Shared' if binary.is_pie else 'Executable'} "
        f"({'stripped' if binary.is_stripped else 'unstripped'})",
        f"Entry Point: 0x{binary.entry_point:x}",
        f"Sections:    {len(binary.sections)} | Imports: {len(binary.imports)} | "
        f"Symbols: {len(binary.symbols)}",
        f"Recovered:   {len(funcs)} functions | {total_blocks} basic blocks | {total_edges} edges",
        "",
        f"{'ADDRESS':<12} {'SIZE':>6} {'BLOCKS':>8} {'EDGES':>7} {'INSNS':>7}  {'NAME'}",
        "-" * 76,
    ]

    for func in funcs:
        lines.append(
            f"0x{func.addr:08x}   {func.size:>6} {func.block_count:>8} "
            f"{func.edge_count:>7} {func.instruction_count:>7}  {func.name}"
        )

    lines.append("-" * 76)
    edge_summary = ", ".join(f"{etype}={count}" for etype, count in sorted(edge_counts.items()))
    lines.append(
        f"TOTAL: {len(funcs)} functions, {total_blocks} blocks, {total_edges} edges"
        + (f" ({edge_summary})" if edge_summary else "")
    )
    return "\n".join(lines)


def format_diff_report(
    binary_a: Binary,
    binary_b: Binary,
    ranked_diffs: Sequence[object],
    top_k: int = 10,
) -> str:
    """Format markdown patch analysis report highlighting top-ranked candidates."""
    lines: list[str] = [
        "# PatchLens Binary Diff & Patch Analysis Report",
        "",
        f"- **Old Binary**: `{binary_a.path}` (`{binary_a.sha256[:16]}...`)",
        f"- **New Binary**: `{binary_b.path}` (`{binary_b.sha256[:16]}...`)",
        "",
        "## Top Security Patch Candidates (Ranked)",
        "",
        "| Rank | Old Function | New Function | Classification | Sim | Patch Score | Tags |",
        "|---:|---|---|---|---:|---:|---|",
    ]

    semantic = [d for d in ranked_diffs if getattr(d, "rank", 0) > 0][:top_k]
    for d in semantic:
        tags = [t.tag_type for t in getattr(d, "security_tags", ())]
        tag_str = ", ".join(f"`{t}`" for t in tags) if tags else "none"
        rank_val = getattr(d, "rank", 0)
        n_a = getattr(d, "name_a", "")
        n_b = getattr(d, "name_b", "")
        c_val = getattr(d, "classification", "")
        s_val = getattr(d, "similarity", 0.0)
        p_val = getattr(d, "patch_score", 0.0)
        lines.append(
            f"| **#{rank_val}** | `{n_a}` | `{n_b}` | `{c_val}` | "
            f"{s_val:.4f} | **{p_val:.4f}** | {tag_str} |"
        )

    lines.extend(["", "## Detailed Instruction Diffs for Top Candidates", ""])
    for d in semantic[:3]:
        name_b = getattr(d, "name_b", "")
        rank = getattr(d, "rank", 0)
        lines.append(f"### Rank #{rank}: `{name_b}`")
        block_diffs = getattr(d, "block_diffs", ())
        has_diff = False
        for bd in block_diffs:
            if getattr(bd, "unified_diff", ()):
                has_diff = True
                lines.append("```diff")
                for uline in getattr(bd, "unified_diff", ()):
                    lines.append(uline)
                lines.append("```")
        if not has_diff:
            lines.append("*(No modified basic block unified diff lines)*")
        lines.append("")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser for `patchlens`."""
    parser = argparse.ArgumentParser(
        prog="patchlens",
        description="PatchLens: ELF binary diffing and security patch analysis tool.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. inspect
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect an ELF binary and print recovered functions, block counts, and edge counts.",
    )
    inspect_parser.add_argument("binary", type=Path, help="Path to the ELF binary to inspect.")
    inspect_parser.add_argument("--json", action="store_true", help="Output Binary model as JSON.")
    inspect_parser.add_argument(
        "--filter", type=str, default=None, help="Optional substring/address filter."
    )

    # 2. diff
    diff_parser = subparsers.add_parser(
        "diff",
        help="Diff two versions of an ELF binary and rank functions by patch likelihood.",
    )
    diff_parser.add_argument("old", type=Path, help="Path to the baseline (unpatched) ELF binary.")
    diff_parser.add_argument("new", type=Path, help="Path to the modified (patched) ELF binary.")
    diff_parser.add_argument("--json", type=Path, default=None, help="Save diff results as JSON.")
    diff_parser.add_argument(
        "--report", type=Path, default=None, help="Save markdown patch report."
    )
    diff_parser.add_argument(
        "--top-k", type=int, default=10, help="Number of top candidates to report (default: 10)."
    )

    # 3. eval
    eval_parser = subparsers.add_parser(
        "eval",
        help="Rerun matching benchmark evaluation and output markdown summary.",
    )
    eval_parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("corpus/binaries"),
        help="Path to corpus binaries directory.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the `patchlens` CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "inspect":
        try:
            binary = analyze_binary(args.binary)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        if args.json:
            print(binary.to_json(indent=2))
        else:
            print(format_inspection_report(binary, function_filter=args.filter))
        return 0

    if args.command == "diff":
        try:
            bin_a = analyze_binary(args.old)
            bin_b = analyze_binary(args.new)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        matcher = FunctionMatcher()
        match_result = matcher.match(bin_a, bin_b)
        diffs = diff_matched_functions(match_result, bin_a, bin_b)
        ranked = score_and_rank_diffs(diffs, bin_b)

        report_md = format_diff_report(bin_a, bin_b, ranked, top_k=args.top_k)
        print(report_md)

        if args.report:
            args.report.write_text(report_md, encoding="utf-8")
        if args.json:
            json_data = [d.to_dict() for d in ranked]
            args.json.write_text(json.dumps(json_data, indent=2) + "\n", encoding="utf-8")
        return 0

    if args.command == "eval":
        tuning, held_out = run_full_evaluation(args.corpus_dir)
        print(f"Evaluated {len(tuning)} tuning scenarios and {len(held_out)} held-out scenarios.")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
