"""ELF binary loader built on pyelftools."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from elftools.elf.constants import SH_FLAGS
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
from elftools.elf.sections import SymbolTableSection

from core.models import Architecture, Binary, ImportEntry, Section, Symbol

_MACHINE_MAP: dict[str, Architecture] = {
    "EM_X86_64": Architecture.X86_64,
    "EM_AARCH64": Architecture.ARM64,
}

_R_X86_64_RELATIVE = 8
_R_AARCH64_RELATIVE = 1027


@dataclass(frozen=True, slots=True)
class LoadedELF:
    """Container holding parsed Binary metadata plus raw section bytes for analysis."""

    binary: Binary
    section_data: dict[str, bytes]
    reloc_text_Addends: tuple[int, ...] = ()

    def read_vaddr(self, vaddr: int, size: int) -> bytes | None:
        """Read `size` bytes starting at virtual address `vaddr` from loaded sections."""
        for sec in self.binary.sections:
            if sec.size > 0 and sec.addr <= vaddr and vaddr + size <= sec.addr + sec.size:
                raw = self.section_data.get(sec.name)
                if raw is not None:
                    offset = vaddr - sec.addr
                    if offset >= 0 and offset + size <= len(raw):
                        return raw[offset : offset + size]
        return None


def _resolve_plt_got_map(
    sections: tuple[Section, ...],
    section_data: dict[str, bytes],
) -> dict[int, int]:
    """Scan .plt.sec, .plt.got, and .plt stubs to map GOT slot address -> PLT stub address."""
    got_to_plt: dict[int, int] = {}
    for sec_name in (".plt.sec", ".plt.got", ".plt"):
        sec = next((s for s in sections if s.name == sec_name), None)
        raw = section_data.get(sec_name)
        if sec is None or raw is None or sec.size == 0:
            continue

        # Each PLT stub is typically 16 bytes (or 8 bytes in some .plt.got sections).
        # Scan for RIP-relative indirect jump: ff 25 <disp32> (or BND-prefixed f2 ff 25 <disp32>)
        idx = 0
        limit = len(raw)
        while idx + 6 <= limit:
            if raw[idx] == 0xFF and raw[idx + 1] == 0x25:
                disp = struct.unpack_from("<i", raw, idx + 2)[0]
                insn_end = sec.addr + idx + 6
                got_addr = (insn_end + disp) & 0xFFFFFFFFFFFFFFFF
                # Determine stub start: 16-byte aligned boundary (or 8-byte for 8-byte .plt.got)
                stride = 8 if (sec_name == ".plt.got" and sec.size % 16 != 0) else 16
                stub_offset = (idx // stride) * stride
                stub_addr = sec.addr + stub_offset
                got_to_plt.setdefault(got_addr, stub_addr)
                idx += 6
            else:
                idx += 1
    return got_to_plt


def _extract_sections(elffile: ELFFile) -> tuple[tuple[Section, ...], dict[str, bytes]]:
    """Extract all ELF sections and cache raw bytes for relevant code/data sections."""
    sections: list[Section] = []
    section_data: dict[str, bytes] = {}
    keep_data_names = {
        ".text",
        ".init",
        ".fini",
        ".plt",
        ".plt.sec",
        ".plt.got",
        ".rodata",
        ".data.rel.ro",
        ".init_array",
        ".fini_array",
        ".eh_frame",
    }

    for sec in elffile.iter_sections():
        name = str(sec.name)
        header = sec.header
        addr = int(header["sh_addr"])
        size = int(header["sh_size"])
        offset = int(header["sh_offset"])
        flags = int(header["sh_flags"])
        is_exec = bool(flags & SH_FLAGS.SHF_EXECINSTR)

        sections.append(
            Section(
                name=name,
                addr=addr,
                size=size,
                offset=offset,
                flags=flags,
                is_exec=is_exec,
            )
        )
        if is_exec or name in keep_data_names or name.startswith(".rodata"):
            section_data[name] = bytes(sec.data())

    return tuple(sections), section_data


def _extract_symbols(
    elffile: ELFFile,
    section_names_by_idx: dict[int, str],
) -> tuple[tuple[Symbol, ...], bool]:
    """Extract symbols from .symtab and .dynsym and determine whether binary is stripped."""
    symbols: list[Symbol] = []
    has_symtab = False

    for sec in elffile.iter_sections():
        if not isinstance(sec, SymbolTableSection):
            continue
        sec_name = str(sec.name)
        is_dynamic = sec_name == ".dynsym"
        if sec_name == ".symtab":
            has_symtab = True

        for sym in sec.iter_symbols():
            raw_name = str(sym.name)
            if not raw_name:
                continue
            clean_name = raw_name.split("@")[0]
            entry = sym.entry
            addr = int(entry["st_value"])
            size = int(entry["st_size"])
            binding = str(entry["st_info"]["bind"])
            sym_type = str(entry["st_info"]["type"])
            shndx = entry["st_shndx"]
            target_sec_name = (
                section_names_by_idx.get(int(shndx)) if isinstance(shndx, int) else None
            )

            symbols.append(
                Symbol(
                    name=clean_name,
                    addr=addr,
                    size=size,
                    binding=binding,
                    sym_type=sym_type,
                    section_name=target_sec_name,
                    is_dynamic=is_dynamic,
                )
            )

    is_stripped = not has_symtab
    return tuple(symbols), is_stripped


def _extract_imports_and_relocs(
    elffile: ELFFile,
    sections: tuple[Section, ...],
    section_data: dict[str, bytes],
) -> tuple[tuple[ImportEntry, ...], tuple[int, ...]]:
    """Extract PLT/GOT imports and R_*_RELATIVE relocation addends pointing into .text."""
    got_to_plt = _resolve_plt_got_map(sections, section_data)
    plt_sec = next((s for s in sections if s.name == ".plt"), None)
    text_sec = next((s for s in sections if s.name == ".text"), None)

    imports: list[ImportEntry] = []
    seen_imports: set[tuple[str, int]] = set()
    reloc_text_addends: set[int] = set()

    for sec in elffile.iter_sections():
        if not isinstance(sec, RelocationSection):
            continue
        sec_name = str(sec.name)
        symtable = elffile.get_section(sec.header["sh_link"])
        has_symtable = isinstance(symtable, SymbolTableSection)

        for idx, reloc in enumerate(sec.iter_relocations()):
            got_addr = int(reloc["r_offset"])
            r_info_type = int(reloc["r_info_type"])
            sym_idx = int(reloc["r_info_sym"])

            # Collect relative relocation addends pointing inside .text (e.g. function tables)
            if reloc.is_RELA() and r_info_type in (_R_X86_64_RELATIVE, _R_AARCH64_RELATIVE):
                addend = int(reloc["r_addend"])
                if text_sec is not None and text_sec.contains(addend):
                    reloc_text_addends.add(addend)

            if not has_symtable or sym_idx == 0:
                continue
            assert isinstance(symtable, SymbolTableSection)
            sym = symtable.get_symbol(sym_idx)
            raw_name = str(sym.name)
            if not raw_name:
                continue
            clean_name = raw_name.split("@")[0]

            plt_addr = got_to_plt.get(got_addr, 0)
            if plt_addr == 0 and sec_name in (".rela.plt", ".rel.plt") and plt_sec is not None:
                # Classic PLT fallback: stub 0 is resolver (16 bytes), stub k+1 is at +16*(k+1)
                candidate = plt_sec.addr + 16 * (idx + 1)
                if plt_sec.contains(candidate):
                    plt_addr = candidate

            key = (clean_name, got_addr)
            if key not in seen_imports:
                seen_imports.add(key)
                imports.append(
                    ImportEntry(
                        name=clean_name,
                        plt_addr=plt_addr,
                        got_addr=got_addr,
                        reloc_type=str(r_info_type),
                    )
                )

    return tuple(imports), tuple(sorted(reloc_text_addends))


def load_elf_from_stream(stream: BinaryIO, path_str: str) -> LoadedELF:
    """Parse an ELF binary from a seekable byte stream."""
    stream.seek(0)
    raw_bytes = stream.read()
    if len(raw_bytes) < 4 or raw_bytes[:4] != b"\x7fELF":
        raise ValueError(f"File is not a valid ELF binary: {path_str}")

    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
    stream.seek(0)
    elffile = ELFFile(stream)

    e_machine = str(elffile.header["e_machine"])
    arch = _MACHINE_MAP.get(e_machine, Architecture.UNKNOWN)
    bits = int(elffile.elfclass)
    endian = "little" if elffile.little_endian else "big"
    e_type = str(elffile.header["e_type"])
    is_pie = e_type == "ET_DYN"
    entry_point = int(elffile.header["e_entry"])

    section_names_by_idx: dict[int, str] = {}
    for idx, sec in enumerate(elffile.iter_sections()):
        section_names_by_idx[idx] = str(sec.name)

    sections, section_data = _extract_sections(elffile)
    symbols, is_stripped = _extract_symbols(elffile, section_names_by_idx)
    imports, reloc_text_addends = _extract_imports_and_relocs(elffile, sections, section_data)

    binary = Binary(
        path=path_str,
        sha256=sha256_hex,
        arch=arch,
        bits=bits,
        endian=endian,
        is_pie=is_pie,
        is_stripped=is_stripped,
        entry_point=entry_point,
        sections=sections,
        symbols=symbols,
        imports=imports,
        functions=(),
    )
    return LoadedELF(
        binary=binary,
        section_data=section_data,
        reloc_text_Addends=reloc_text_addends,
    )


def load_elf(path: str | Path) -> LoadedELF:
    """Load an ELF binary from disk and extract metadata, sections, symbols, and imports."""
    resolved = Path(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"ELF binary not found: {resolved}")
    with resolved.open("rb") as f:
        return load_elf_from_stream(f, str(resolved))
