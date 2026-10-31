"""Shared pytest fixtures for PatchLens unit and integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

CORPUS_BIN_DIR = Path(__file__).resolve().parent.parent / "corpus" / "binaries"


@pytest.fixture(scope="session")
def zlib_1211_gcc_o2_unstripped() -> Path:
    """Path to unstripped zlib 1.2.11 built with gcc -O2."""
    path = CORPUS_BIN_DIR / "libz-1.2.11-gcc-O2-unstripped.so"
    if not path.is_file():
        pytest.skip(f"Corpus binary not built: {path}")
    return path


@pytest.fixture(scope="session")
def zlib_1211_gcc_o2_stripped() -> Path:
    """Path to stripped zlib 1.2.11 built with gcc -O2."""
    path = CORPUS_BIN_DIR / "libz-1.2.11-gcc-O2-stripped.so"
    if not path.is_file():
        pytest.skip(f"Corpus binary not built: {path}")
    return path


@pytest.fixture(scope="session")
def zlib_1212_gcc_o0_unstripped() -> Path:
    """Path to unstripped zlib 1.2.12 built with gcc -O0."""
    path = CORPUS_BIN_DIR / "libz-1.2.12-gcc-O0-unstripped.so"
    if not path.is_file():
        pytest.skip(f"Corpus binary not built: {path}")
    return path
