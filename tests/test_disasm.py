"""Tests for core/disasm.py recursive descent, linear sweep, and function recovery accuracy."""

from __future__ import annotations

from pathlib import Path

from core.cfg import recover_all_functions
from core.disasm import disassemble_text
from core.loader import load_elf

CORPUS_BIN_DIR = Path(__file__).resolve().parent.parent / "corpus" / "binaries"


def _symtab_text_func_count(binary_path: Path) -> int:
    """Return number of unique STT_FUNC symbol addresses inside .text from .symtab."""
    loaded = load_elf(binary_path)
    text_sec = loaded.binary.get_section(".text")
    assert text_sec is not None
    addrs = {
        s.addr
        for s in loaded.binary.symbols
        if not s.is_dynamic and s.sym_type == "STT_FUNC" and text_sec.contains(s.addr)
    }
    return len(addrs)


def test_unstripped_function_recovery_within_5_percent(
    zlib_1211_gcc_o2_unstripped: Path,
) -> None:
    loaded = load_elf(zlib_1211_gcc_o2_unstripped)
    disasm = disassemble_text(loaded)
    funcs = recover_all_functions(loaded, disasm)

    symtab_count = _symtab_text_func_count(zlib_1211_gcc_o2_unstripped)
    recovered_count = len(funcs)
    delta_ratio = abs(recovered_count - symtab_count) / symtab_count

    assert symtab_count > 0
    assert delta_ratio <= 0.05, (
        f"Recovered function count {recovered_count} differs from .symtab count "
        f"{symtab_count} by {delta_ratio:.2%}"
    )


def test_stripped_function_recovery_accuracy(
    zlib_1211_gcc_o2_unstripped: Path,
    zlib_1211_gcc_o2_stripped: Path,
) -> None:
    symtab_count = _symtab_text_func_count(zlib_1211_gcc_o2_unstripped)

    loaded_stripped = load_elf(zlib_1211_gcc_o2_stripped)
    assert loaded_stripped.binary.is_stripped is True

    disasm_stripped = disassemble_text(loaded_stripped)
    funcs_stripped = recover_all_functions(loaded_stripped, disasm_stripped)
    recovered_stripped = len(funcs_stripped)

    delta_ratio = abs(recovered_stripped - symtab_count) / symtab_count
    assert delta_ratio <= 0.05, (
        f"Stripped recovered function count {recovered_stripped} differs from ground-truth "
        f".symtab count {symtab_count} by {delta_ratio:.2%}"
    )


def test_all_unstripped_corpus_variants_within_5_percent() -> None:
    unstripped_files = sorted(CORPUS_BIN_DIR.glob("*-unstripped.so"))
    assert len(unstripped_files) == 8

    for bin_path in unstripped_files:
        loaded = load_elf(bin_path)
        disasm = disassemble_text(loaded)
        funcs = recover_all_functions(loaded, disasm)
        sym_count = _symtab_text_func_count(bin_path)
        delta = abs(len(funcs) - sym_count) / sym_count
        assert delta <= 0.05, f"{bin_path.name}: {len(funcs)} vs {sym_count} ({delta:.2%})"
