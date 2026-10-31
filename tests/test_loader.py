"""Unit and integration tests for core/loader.py and core/arch.py."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from core.arch import ARM64Profile, X86_64Profile, get_arch_profile
from core.loader import load_elf, load_elf_from_stream
from core.models import Architecture, Instruction


def test_load_elf_unstripped_and_stripped(
    zlib_1211_gcc_o2_unstripped: Path,
    zlib_1211_gcc_o2_stripped: Path,
) -> None:
    loaded_unstripped = load_elf(zlib_1211_gcc_o2_unstripped)
    b_un = loaded_unstripped.binary
    assert b_un.arch == Architecture.X86_64
    assert b_un.bits == 64
    assert b_un.endian == "little"
    assert b_un.is_pie is True
    assert b_un.is_stripped is False
    assert len(b_un.sha256) == 64

    text_sec = b_un.get_section(".text")
    assert text_sec is not None
    assert text_sec.is_exec is True
    assert text_sec.size > 0

    # Verify symbol table contains known zlib functions
    sym_names = {s.name for s in b_un.symbols if s.sym_type == "STT_FUNC"}
    assert "adler32" in sym_names
    assert "deflate" in sym_names
    assert "inflate" in sym_names
    assert "_tr_flush_block" in sym_names

    # Verify PLT/GOT imports extracted
    import_names = {imp.name for imp in b_un.imports}
    assert "malloc" in import_names or "free" in import_names or "memcpy" in import_names

    # Verify read_vaddr reads .text bytes accurately
    head = loaded_unstripped.read_vaddr(text_sec.addr, 4)
    assert head is not None
    assert len(head) == 4
    assert loaded_unstripped.read_vaddr(0xFFFFFFFFFFFF0000, 4) is None

    # Verify stripped binary detection
    loaded_stripped = load_elf(zlib_1211_gcc_o2_stripped)
    assert loaded_stripped.binary.is_stripped is True


def test_load_elf_errors(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_elf(tmp_path / "does_not_exist.so")

    bad_stream = io.BytesIO(b"NOT_AN_ELF_FILE")
    with pytest.raises(ValueError, match="not a valid ELF"):
        load_elf_from_stream(bad_stream, "bad.bin")


def test_arch_profiles() -> None:
    x86_prof = get_arch_profile(Architecture.X86_64)
    assert isinstance(x86_prof, X86_64Profile)
    assert x86_prof.arch == Architecture.X86_64
    md = x86_prof.create_disassembler("little")
    assert md is not None

    assert x86_prof.padding_length(b"\x90\x90", 0) == 1
    assert x86_prof.padding_length(b"\x66\x90", 0) == 2
    assert x86_prof.padding_length(b"\x0f\x1f\x44\x00\x00", 0) == 5
    assert x86_prof.padding_length(b"\x00\x00", 0) == 2
    assert x86_prof.padding_length(b"\x55\x48\x89\xe5", 0) == 0

    assert x86_prof.matches_prologue(b"\xf3\x0f\x1e\xfa\x55\x48\x89\xe5", 0) is True
    assert x86_prof.matches_prologue(b"\x55\x48\x89\xe5", 0) is True
    assert x86_prof.matches_prologue(b"\x41\x57\x41\x56\x55\x53", 0) is True
    assert x86_prof.matches_prologue(b"\x48\x83\xec\x18", 0) is True
    assert x86_prof.matches_prologue(b"\xc3\x90\x90\x90", 0) is False

    arm_prof = get_arch_profile(Architecture.ARM64)
    assert isinstance(arm_prof, ARM64Profile)
    assert arm_prof.arch == Architecture.ARM64
    arm_md = arm_prof.create_disassembler("little")
    assert arm_md is not None
    assert arm_prof.padding_length(b"\x1f\x20\x03\xd5", 0) == 4
    assert arm_prof.matches_prologue(b"\x3f\x23\x03\xd5", 0) is True

    ret_insn = Instruction(
        addr=0x1000, size=4, mnemonic="ret", op_str="", raw_bytes=b"\xc0\x03\x5f\xd6"
    )
    assert arm_prof.is_ret(ret_insn) is True
    assert arm_prof.is_call(ret_insn) is False

    with pytest.raises(ValueError, match="Unsupported architecture"):
        get_arch_profile(Architecture.UNKNOWN)
