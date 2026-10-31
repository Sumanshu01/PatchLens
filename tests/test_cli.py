"""Tests for the `patchlens inspect <binary>` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from core.cli import main


def test_cli_inspect_table_output(
    zlib_1211_gcc_o2_unstripped: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["inspect", str(zlib_1211_gcc_o2_unstripped)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "ADDRESS" in captured.out
    assert "BLOCKS" in captured.out
    assert "EDGES" in captured.out
    assert "adler32" in captured.out
    assert "TOTAL:" in captured.out


def test_cli_inspect_filter_and_json(
    zlib_1211_gcc_o2_unstripped: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["inspect", str(zlib_1211_gcc_o2_unstripped), "--filter", "adler32"])
    assert rc == 0
    out_filtered = capsys.readouterr().out
    assert "adler32" in out_filtered

    rc_json = main(["inspect", str(zlib_1211_gcc_o2_unstripped), "--json"])
    assert rc_json == 0
    out_json = capsys.readouterr().out
    parsed = json.loads(out_json)
    assert parsed["arch"] == "x86_64"
    assert len(parsed["functions"]) > 80


def test_cli_inspect_missing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["inspect", str(tmp_path / "missing.so")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Error:" in err


def test_cli_diff_subcommand(
    zlib_1211_gcc_o2_stripped: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rep_path = tmp_path / "report.md"
    json_path = tmp_path / "diff.json"

    rc = main(
        [
            "diff",
            str(zlib_1211_gcc_o2_stripped),
            str(zlib_1211_gcc_o2_stripped),
            "--report",
            str(rep_path),
            "--json",
            str(json_path),
            "--top-k",
            "5",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "Top Security Patch Candidates" in captured.out
    assert rep_path.is_file()
    assert json_path.is_file()

    # Test error handling on missing diff files
    rc_err = main(["diff", str(tmp_path / "missing1.so"), str(tmp_path / "missing2.so")])
    assert rc_err == 1


def test_cli_eval_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["eval"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Evaluated" in captured.out
