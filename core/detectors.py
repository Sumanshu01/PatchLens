"""Security-patch pattern and change-type heuristic detectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from core.models import BasicBlock, Function


@dataclass(frozen=True, slots=True)
class SecurityTag:
    """Security change pattern tag emitted by a heuristic detector."""

    tag_type: str
    description: str
    confidence: float
    block_ids_a: tuple[int, ...]
    block_ids_b: tuple[int, ...]
    evidence: str

    def to_dict(self) -> dict[str, object]:
        return {
            "tag_type": self.tag_type,
            "description": self.description,
            "confidence": round(self.confidence, 4),
            "block_ids_a": list(self.block_ids_a),
            "block_ids_b": list(self.block_ids_b),
            "evidence": self.evidence,
        }


# Mapping of common unsafe C library functions to safer bounded replacements
_UNSAFE_TO_SAFE_CALLEES: dict[str, str] = {
    "strcpy": "strncpy",
    "strcat": "strncat",
    "sprintf": "snprintf",
    "vsprintf": "vsnprintf",
    "gets": "fgets",
    "alloca": "malloc",
    "sbrk": "mmap",
}

_SIGNED_TO_UNSIGNED_JUMPS: dict[str, str] = {
    "jg": "ja",
    "jge": "jae",
    "jl": "jb",
    "jle": "jbe",
}
_UNSIGNED_TO_SIGNED_JUMPS: dict[str, str] = {v: k for k, v in _SIGNED_TO_UNSIGNED_JUMPS.items()}


class SecurityDetector(ABC):
    """Abstract base class for security-patch pattern detectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the security change detector."""

    @abstractmethod
    def detect(
        self,
        func_a: Function,
        func_b: Function,
        block_matches: Sequence[tuple[BasicBlock | None, BasicBlock | None]],
        callees_a: frozenset[str],
        callees_b: frozenset[str],
    ) -> Sequence[SecurityTag]:
        """Detect security patterns between function A and function B."""


class AddedBoundsCheckDetector(SecurityDetector):
    """Detects newly added bounds/length checks guarding memory writes, buffer access, or calls."""

    @property
    def name(self) -> str:
        return "added_bounds_check"

    def detect(
        self,
        func_a: Function,
        func_b: Function,
        block_matches: Sequence[tuple[BasicBlock | None, BasicBlock | None]],
        callees_a: frozenset[str],
        callees_b: frozenset[str],
    ) -> Sequence[SecurityTag]:
        tags: list[SecurityTag] = []
        bounds_jumps = {"ja", "jae", "jbe", "jb", "jg", "jge", "jl", "jle"}

        # Look at blocks added in B or modified in B
        for b_a, b_b in block_matches:
            if b_b is None:
                continue

            insns_b = b_b.instructions
            if len(insns_b) < 2:
                continue

            for idx in range(len(insns_b) - 1):
                i1 = insns_b[idx]
                i2 = insns_b[idx + 1]

                # Pattern: cmp/sub reg, imm/reg followed by conditional bounds branch
                if i1.mnemonic in ("cmp", "sub") and i2.mnemonic in bounds_jumps:
                    # Check if this comparison is absent in corresponding block in A
                    is_new = True
                    if b_a is not None:
                        for prev_i in b_a.instructions:
                            if prev_i.mnemonic == i1.mnemonic and prev_i.op_str == i1.op_str:
                                is_new = False
                                break

                    if is_new:
                        evidence = (
                            f"New bounds guard: '{i1.mnemonic} {i1.op_str}' + "
                            f"'{i2.mnemonic} {i2.op_str}'"
                        )
                        tags.append(
                            SecurityTag(
                                tag_type="added_bounds_check",
                                description="Added bounds check guarding memory write or branch",
                                confidence=0.90,
                                block_ids_a=() if b_a is None else (b_a.start_addr,),
                                block_ids_b=(b_b.start_addr,),
                                evidence=evidence,
                            )
                        )
                        break

        return tags


class AddedNullErrorCheckDetector(SecurityDetector):
    """Detects newly added NULL or error-return checks (e.g. test reg, reg + je/jne)."""

    @property
    def name(self) -> str:
        return "added_null_error_check"

    def detect(
        self,
        func_a: Function,
        func_b: Function,
        block_matches: Sequence[tuple[BasicBlock | None, BasicBlock | None]],
        callees_a: frozenset[str],
        callees_b: frozenset[str],
    ) -> Sequence[SecurityTag]:
        tags: list[SecurityTag] = []

        for b_a, b_b in block_matches:
            if b_b is None:
                continue

            insns_b = b_b.instructions
            for idx in range(len(insns_b) - 1):
                i1 = insns_b[idx]
                i2 = insns_b[idx + 1]

                # Check for zero/null test: test r, r or cmp r, 0 followed by je/jne
                is_null_test = False
                if i1.mnemonic == "test" and "," in i1.op_str:
                    ops = [o.strip() for o in i1.op_str.split(",")]
                    if len(ops) == 2 and ops[0] == ops[1]:
                        is_null_test = True
                elif i1.mnemonic == "cmp" and i1.op_str.endswith(", 0"):
                    is_null_test = True

                if is_null_test and i2.mnemonic in ("je", "jne", "jz", "jnz"):
                    is_new = True
                    if b_a is not None:
                        for prev_i in b_a.instructions:
                            if prev_i.mnemonic == i1.mnemonic and prev_i.op_str == i1.op_str:
                                is_new = False
                                break

                    if is_new:
                        ev_str = f"New zero check: '{i1.mnemonic} {i1.op_str}' + '{i2.mnemonic}'"
                        tags.append(
                            SecurityTag(
                                tag_type="added_null_error_check",
                                description="Added NULL or zero error-return check",
                                confidence=0.88,
                                block_ids_a=() if b_a is None else (b_a.start_addr,),
                                block_ids_b=(b_b.start_addr,),
                                evidence=ev_str,
                            )
                        )
                        break

        return tags


class IntegerWidthSignednessDetector(SecurityDetector):
    """Detects integer width changes (e.g. 32-bit to 64-bit movsxd) and signed/unsigned flips."""

    @property
    def name(self) -> str:
        return "integer_width_signedness"

    def detect(
        self,
        func_a: Function,
        func_b: Function,
        block_matches: Sequence[tuple[BasicBlock | None, BasicBlock | None]],
        callees_a: frozenset[str],
        callees_b: frozenset[str],
    ) -> Sequence[SecurityTag]:
        tags: list[SecurityTag] = []

        for b_a, b_b in block_matches:
            if b_a is None or b_b is None:
                continue

            # Check 1: Added movsxd or sign extension
            has_movsxd_a = any(i.mnemonic == "movsxd" for i in b_a.instructions)
            has_movsxd_b = any(i.mnemonic == "movsxd" for i in b_b.instructions)
            if not has_movsxd_a and has_movsxd_b:
                tags.append(
                    SecurityTag(
                        tag_type="integer_width_signedness",
                        description="Added 64-bit integer sign-extension (movsxd)",
                        confidence=0.85,
                        block_ids_a=(b_a.start_addr,),
                        block_ids_b=(b_b.start_addr,),
                        evidence="Introduced movsxd instruction for 64-bit index/size extension",
                    )
                )

            # Check 2: Signed vs unsigned conditional branch flip
            last_a = b_a.instructions[-1] if b_a.instructions else None
            last_b = b_b.instructions[-1] if b_b.instructions else None
            if last_a and last_b:
                m_a = last_a.mnemonic.lower()
                m_b = last_b.mnemonic.lower()
                if (m_a in _SIGNED_TO_UNSIGNED_JUMPS and _SIGNED_TO_UNSIGNED_JUMPS[m_a] == m_b) or (
                    m_a in _UNSIGNED_TO_SIGNED_JUMPS and _UNSIGNED_TO_SIGNED_JUMPS[m_a] == m_b
                ):
                    tags.append(
                        SecurityTag(
                            tag_type="integer_width_signedness",
                            description=f"Branch signedness conversion: '{m_a}' -> '{m_b}'",
                            confidence=0.92,
                            block_ids_a=(b_a.start_addr,),
                            block_ids_b=(b_b.start_addr,),
                            evidence=f"Changed conditional branch signedness from {m_a} to {m_b}",
                        )
                    )

        return tags


class ReplacedUnsafeCallDetector(SecurityDetector):
    """Detects replacement of unsafe C functions with safer, length-bounded counterparts."""

    @property
    def name(self) -> str:
        return "replaced_unsafe_call"

    def detect(
        self,
        func_a: Function,
        func_b: Function,
        block_matches: Sequence[tuple[BasicBlock | None, BasicBlock | None]],
        callees_a: frozenset[str],
        callees_b: frozenset[str],
    ) -> Sequence[SecurityTag]:
        tags: list[SecurityTag] = []

        for unsafe, safe in _UNSAFE_TO_SAFE_CALLEES.items():
            if unsafe in callees_a and safe in callees_b:
                tags.append(
                    SecurityTag(
                        tag_type="replaced_unsafe_call",
                        description=f"Replaced unsafe call '{unsafe}' with '{safe}'",
                        confidence=0.98,
                        block_ids_a=(),
                        block_ids_b=(),
                        evidence=f"Replaced callee {unsafe} with safer bounded {safe}",
                    )
                )

        return tags


class NewEarlyExitDetector(SecurityDetector):
    """Detects newly introduced early exit or return paths from newly added basic blocks."""

    @property
    def name(self) -> str:
        return "new_early_exit"

    def detect(
        self,
        func_a: Function,
        func_b: Function,
        block_matches: Sequence[tuple[BasicBlock | None, BasicBlock | None]],
        callees_a: frozenset[str],
        callees_b: frozenset[str],
    ) -> Sequence[SecurityTag]:
        tags: list[SecurityTag] = []

        # Find basic blocks in B that are newly added and terminate with `ret`
        for b_a, b_b in block_matches:
            if (
                b_a is None
                and b_b is not None
                and b_b.instructions
                and b_b.instructions[-1].mnemonic in ("ret", "retq")
                and len(func_b.blocks) > 1
            ):
                ev = f"Added basic block at 0x{b_b.start_addr:x} terminating in early ret"
                tags.append(
                    SecurityTag(
                        tag_type="new_early_exit",
                        description="New early-return exit path introduced",
                        confidence=0.82,
                        block_ids_a=(),
                        block_ids_b=(b_b.start_addr,),
                        evidence=ev,
                    )
                )
                break

        return tags


ALL_DETECTORS: tuple[SecurityDetector, ...] = (
    AddedBoundsCheckDetector(),
    AddedNullErrorCheckDetector(),
    IntegerWidthSignednessDetector(),
    ReplacedUnsafeCallDetector(),
    NewEarlyExitDetector(),
)


def run_all_detectors(
    func_a: Function,
    func_b: Function,
    block_matches: Sequence[tuple[BasicBlock | None, BasicBlock | None]],
    callees_a: frozenset[str],
    callees_b: frozenset[str],
    detectors: Sequence[SecurityDetector] | None = None,
) -> tuple[SecurityTag, ...]:
    """Execute all configured security-patch detectors and return detected tags."""
    active_detectors = detectors or ALL_DETECTORS
    tags: list[SecurityTag] = []
    for d in active_detectors:
        for tag in d.detect(func_a, func_b, block_matches, callees_a, callees_b):
            tags.append(tag)
    return tuple(tags)
