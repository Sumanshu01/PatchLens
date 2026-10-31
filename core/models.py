"""Immutable data models for PatchLens binary representation and JSON serialization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Architecture(StrEnum):
    """Supported ELF target architectures."""

    X86_64 = "x86_64"
    ARM64 = "aarch64"
    UNKNOWN = "unknown"


class EdgeType(StrEnum):
    """Control-flow graph edge classification."""

    FALLTHROUGH = "fallthrough"
    JUMP = "jump"
    CONDITIONAL_TRUE = "conditional-true"
    CONDITIONAL_FALSE = "conditional-false"
    CALL = "call"


@dataclass(frozen=True, slots=True)
class Section:
    """Metadata for an ELF section."""

    name: str
    addr: int
    size: int
    offset: int
    flags: int
    is_exec: bool

    def contains(self, addr: int) -> bool:
        """Return True if virtual address `addr` lies within this section."""
        return self.addr <= addr < self.addr + self.size

    def to_dict(self) -> dict[str, Any]:
        """Serialize section to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "addr": self.addr,
            "size": self.size,
            "offset": self.offset,
            "flags": self.flags,
            "is_exec": self.is_exec,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Section:
        """Deserialize a Section from a dictionary."""
        return cls(
            name=str(data["name"]),
            addr=int(data["addr"]),
            size=int(data["size"]),
            offset=int(data["offset"]),
            flags=int(data["flags"]),
            is_exec=bool(data["is_exec"]),
        )


@dataclass(frozen=True, slots=True)
class Symbol:
    """ELF symbol entry from .symtab or .dynsym."""

    name: str
    addr: int
    size: int
    binding: str
    sym_type: str
    section_name: str | None = None
    is_dynamic: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize symbol to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "addr": self.addr,
            "size": self.size,
            "binding": self.binding,
            "sym_type": self.sym_type,
            "section_name": self.section_name,
            "is_dynamic": self.is_dynamic,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Symbol:
        """Deserialize a Symbol from a dictionary."""
        sec = data.get("section_name")
        return cls(
            name=str(data["name"]),
            addr=int(data["addr"]),
            size=int(data["size"]),
            binding=str(data["binding"]),
            sym_type=str(data["sym_type"]),
            section_name=str(sec) if sec is not None else None,
            is_dynamic=bool(data.get("is_dynamic", False)),
        )


@dataclass(frozen=True, slots=True)
class ImportEntry:
    """Imported external function resolved through PLT/GOT relocations."""

    name: str
    plt_addr: int
    got_addr: int
    reloc_type: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize import entry to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "plt_addr": self.plt_addr,
            "got_addr": self.got_addr,
            "reloc_type": self.reloc_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImportEntry:
        """Deserialize an ImportEntry from a dictionary."""
        return cls(
            name=str(data["name"]),
            plt_addr=int(data["plt_addr"]),
            got_addr=int(data["got_addr"]),
            reloc_type=str(data["reloc_type"]),
        )


@dataclass(frozen=True, slots=True)
class Instruction:
    """Single disassembled machine instruction."""

    addr: int
    size: int
    mnemonic: str
    op_str: str
    raw_bytes: bytes
    groups: tuple[str, ...] = ()
    branch_target: int | None = None
    call_target: int | None = None
    rip_target: int | None = None

    @property
    def end_addr(self) -> int:
        """Address immediately following this instruction."""
        return self.addr + self.size

    def to_dict(self) -> dict[str, Any]:
        """Serialize instruction to a JSON-compatible dictionary."""
        return {
            "addr": self.addr,
            "size": self.size,
            "mnemonic": self.mnemonic,
            "op_str": self.op_str,
            "raw_bytes": self.raw_bytes.hex(),
            "groups": list(self.groups),
            "branch_target": self.branch_target,
            "call_target": self.call_target,
            "rip_target": self.rip_target,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Instruction:
        """Deserialize an Instruction from a dictionary."""
        bt = data.get("branch_target")
        ct = data.get("call_target")
        rt = data.get("rip_target")
        return cls(
            addr=int(data["addr"]),
            size=int(data["size"]),
            mnemonic=str(data["mnemonic"]),
            op_str=str(data["op_str"]),
            raw_bytes=bytes.fromhex(str(data["raw_bytes"])),
            groups=tuple(str(g) for g in data.get("groups", [])),
            branch_target=int(bt) if bt is not None else None,
            call_target=int(ct) if ct is not None else None,
            rip_target=int(rt) if rt is not None else None,
        )

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialize instruction to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> Instruction:
        """Deserialize an Instruction from a JSON string."""
        data: dict[str, Any] = json.loads(raw)
        return cls.from_dict(data)


@dataclass(frozen=True, slots=True)
class Edge:
    """Directed control-flow edge between basic blocks (or call targets)."""

    src: int
    dst: int
    edge_type: EdgeType

    def to_dict(self) -> dict[str, Any]:
        """Serialize edge to a JSON-compatible dictionary."""
        return {
            "src": self.src,
            "dst": self.dst,
            "edge_type": self.edge_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        """Deserialize an Edge from a dictionary."""
        return cls(
            src=int(data["src"]),
            dst=int(data["dst"]),
            edge_type=EdgeType(str(data["edge_type"])),
        )


@dataclass(frozen=True, slots=True)
class JumpTable:
    """Recovered indirect branch jump table."""

    insn_addr: int
    table_addr: int
    targets: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize jump table to a JSON-compatible dictionary."""
        return {
            "insn_addr": self.insn_addr,
            "table_addr": self.table_addr,
            "targets": list(self.targets),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JumpTable:
        """Deserialize a JumpTable from a dictionary."""
        return cls(
            insn_addr=int(data["insn_addr"]),
            table_addr=int(data["table_addr"]),
            targets=tuple(int(t) for t in data.get("targets", [])),
        )


@dataclass(frozen=True, slots=True)
class BasicBlock:
    """Contiguous sequence of instructions with a single entry and single exit."""

    start_addr: int
    end_addr: int
    instructions: tuple[Instruction, ...]
    out_edges: tuple[Edge, ...] = ()

    @property
    def size(self) -> int:
        """Byte size of the basic block."""
        return self.end_addr - self.start_addr

    @property
    def instruction_count(self) -> int:
        """Number of instructions in the basic block."""
        return len(self.instructions)

    def to_dict(self) -> dict[str, Any]:
        """Serialize basic block to a JSON-compatible dictionary."""
        return {
            "start_addr": self.start_addr,
            "end_addr": self.end_addr,
            "instructions": [i.to_dict() for i in self.instructions],
            "out_edges": [e.to_dict() for e in self.out_edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BasicBlock:
        """Deserialize a BasicBlock from a dictionary."""
        return cls(
            start_addr=int(data["start_addr"]),
            end_addr=int(data["end_addr"]),
            instructions=tuple(Instruction.from_dict(i) for i in data.get("instructions", [])),
            out_edges=tuple(Edge.from_dict(e) for e in data.get("out_edges", [])),
        )

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialize basic block to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> BasicBlock:
        """Deserialize a BasicBlock from a JSON string."""
        data: dict[str, Any] = json.loads(raw)
        return cls.from_dict(data)


@dataclass(frozen=True, slots=True)
class Function:
    """Recovered function and its control-flow graph representation."""

    addr: int
    size: int
    name: str
    is_symbol_backed: bool
    blocks: tuple[BasicBlock, ...]
    edges: tuple[Edge, ...]
    jump_tables: tuple[JumpTable, ...] = ()
    tail_calls: tuple[int, ...] = ()
    call_targets: tuple[int, ...] = ()

    @property
    def block_count(self) -> int:
        """Number of basic blocks in this function."""
        return len(self.blocks)

    @property
    def edge_count(self) -> int:
        """Number of control-flow edges in this function."""
        return len(self.edges)

    @property
    def instruction_count(self) -> int:
        """Total number of instructions across all basic blocks."""
        return sum(len(b.instructions) for b in self.blocks)

    def to_dict(self) -> dict[str, Any]:
        """Serialize function to a JSON-compatible dictionary."""
        return {
            "addr": self.addr,
            "size": self.size,
            "name": self.name,
            "is_symbol_backed": self.is_symbol_backed,
            "blocks": [b.to_dict() for b in self.blocks],
            "edges": [e.to_dict() for e in self.edges],
            "jump_tables": [jt.to_dict() for jt in self.jump_tables],
            "tail_calls": list(self.tail_calls),
            "call_targets": list(self.call_targets),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Function:
        """Deserialize a Function from a dictionary."""
        return cls(
            addr=int(data["addr"]),
            size=int(data["size"]),
            name=str(data["name"]),
            is_symbol_backed=bool(data["is_symbol_backed"]),
            blocks=tuple(BasicBlock.from_dict(b) for b in data.get("blocks", [])),
            edges=tuple(Edge.from_dict(e) for e in data.get("edges", [])),
            jump_tables=tuple(JumpTable.from_dict(jt) for jt in data.get("jump_tables", [])),
            tail_calls=tuple(int(t) for t in data.get("tail_calls", [])),
            call_targets=tuple(int(c) for c in data.get("call_targets", [])),
        )

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialize function to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> Function:
        """Deserialize a Function from a JSON string."""
        data: dict[str, Any] = json.loads(raw)
        return cls.from_dict(data)


@dataclass(frozen=True, slots=True)
class Binary:
    """Top-level immutable representation of an analyzed ELF binary."""

    path: str
    sha256: str
    arch: Architecture
    bits: int
    endian: str
    is_pie: bool
    is_stripped: bool
    entry_point: int
    sections: tuple[Section, ...]
    symbols: tuple[Symbol, ...]
    imports: tuple[ImportEntry, ...]
    functions: tuple[Function, ...] = ()

    def get_section(self, name: str) -> Section | None:
        """Look up a section by exact name."""
        for sec in self.sections:
            if sec.name == name:
                return sec
        return None

    def get_function(self, key: str | int) -> Function | None:
        """Look up a function by name or virtual address."""
        for func in self.functions:
            if isinstance(key, int) and func.addr == key:
                return func
            if isinstance(key, str) and func.name == key:
                return func
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize binary to a JSON-compatible dictionary."""
        return {
            "path": self.path,
            "sha256": self.sha256,
            "arch": self.arch.value,
            "bits": self.bits,
            "endian": self.endian,
            "is_pie": self.is_pie,
            "is_stripped": self.is_stripped,
            "entry_point": self.entry_point,
            "sections": [s.to_dict() for s in self.sections],
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": [i.to_dict() for i in self.imports],
            "functions": [f.to_dict() for f in self.functions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Binary:
        """Deserialize a Binary from a dictionary."""
        return cls(
            path=str(data["path"]),
            sha256=str(data["sha256"]),
            arch=Architecture(str(data["arch"])),
            bits=int(data["bits"]),
            endian=str(data["endian"]),
            is_pie=bool(data["is_pie"]),
            is_stripped=bool(data["is_stripped"]),
            entry_point=int(data["entry_point"]),
            sections=tuple(Section.from_dict(s) for s in data.get("sections", [])),
            symbols=tuple(Symbol.from_dict(s) for s in data.get("symbols", [])),
            imports=tuple(ImportEntry.from_dict(i) for i in data.get("imports", [])),
            functions=tuple(Function.from_dict(f) for f in data.get("functions", [])),
        )

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialize binary to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> Binary:
        """Deserialize a Binary from a JSON string."""
        data: dict[str, Any] = json.loads(raw)
        return cls.from_dict(data)
