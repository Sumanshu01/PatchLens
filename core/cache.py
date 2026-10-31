"""Analysis caching for PatchLens binary diffing, keyed by binary SHA-256."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

from core.cfg import analyze_binary
from core.models import Binary

DEFAULT_CACHE_DIR = Path(".patchlens_cache")


class AnalysisCache:
    """Persistent on-disk and in-memory cache for analyzed Binary instances."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self._memory_cache: dict[str, Binary] = {}

    def _ensure_dir(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, binary_path: Path | str, sha256_hex: str | None = None) -> Binary | None:
        """Retrieve an analyzed Binary from memory or disk cache."""
        path = Path(binary_path)
        # Check in-memory cache by path or sha256
        if sha256_hex and sha256_hex in self._memory_cache:
            return self._memory_cache[sha256_hex]
        path_key = str(path.resolve())
        if path_key in self._memory_cache:
            return self._memory_cache[path_key]

        if not path.is_file():
            return None

        # Check on-disk cache if sha256 is known
        if sha256_hex:
            disk_path = self.cache_dir / f"{sha256_hex}.json"
            if disk_path.is_file():
                try:
                    data = json.loads(disk_path.read_text(encoding="utf-8"))
                    binary = Binary.from_dict(data)
                    self._memory_cache[sha256_hex] = binary
                    self._memory_cache[path_key] = binary
                    return binary
                except Exception:
                    pass
        return None

    def put(self, binary: Binary) -> None:
        """Store an analyzed Binary into memory and on disk."""
        self._memory_cache[binary.sha256] = binary
        self._memory_cache[str(Path(binary.path).resolve())] = binary
        self._ensure_dir()
        disk_path = self.cache_dir / f"{binary.sha256}.json"
        with contextlib.suppress(Exception):
            disk_path.write_text(binary.to_json(indent=2), encoding="utf-8")

    def get_or_analyze(self, binary_path: Path | str) -> Binary:
        """Retrieve analyzed Binary from cache, or analyze and cache it."""
        path = Path(binary_path)
        path_key = str(path.resolve())
        if path_key in self._memory_cache:
            return self._memory_cache[path_key]

        cached = self.get(path)
        if cached is not None:
            return cached

        analyzed = analyze_binary(path)
        self.put(analyzed)
        return analyzed

    def clear(self) -> None:
        """Clear memory cache and remove on-disk cache files."""
        self._memory_cache.clear()
        if self.cache_dir.is_dir():
            for p in self.cache_dir.glob("*.json"):
                with contextlib.suppress(Exception):
                    p.unlink()


# Global singleton default cache instance
GLOBAL_CACHE = AnalysisCache()
