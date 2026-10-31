"""Builder for cJSON 1.7.11 and 1.7.12 (CVE-2019-1010239) corpus binaries."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

CORPUS_DIR = Path(__file__).resolve().parent
CJSON_DIR = CORPUS_DIR / "cjson"
BINARIES_DIR = CJSON_DIR / "binaries"
CACHE_DIR = CORPUS_DIR / ".build_cache" / "cjson-git"
MANIFEST_PATH = CJSON_DIR / "manifest.json"

CJSON_REPO_URL = "https://github.com/DaveGamble/cJSON.git"
CJSON_VERSIONS: tuple[str, ...] = ("1.7.11", "1.7.12")
CVE_ID = "CVE-2019-1010239"

BUILD_VARIANTS: tuple[tuple[str, str, str], ...] = (
    ("gcc-O0", "gcc", "-O0"),
    ("gcc-O2", "gcc", "-O2"),
    ("clang-O2", "clang", "-O2"),
)


def _to_wsl_path(win_path: Path) -> str:
    resolved = win_path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", 1)[-1].lstrip("/")
    return f"/mnt/{drive}/{tail}"


def _run_linux_cmd(cmd: str, cwd: Path | None = None) -> str:
    if os.name == "nt":
        if cwd is not None:
            wsl_cwd = _to_wsl_path(cwd)
            full_cmd = f"cd '{wsl_cwd}' && {cmd}"
        else:
            full_cmd = cmd
        proc = subprocess.run(
            ["wsl", "bash", "-c", full_cmd],
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout
    proc = subprocess.run(
        ["bash", "-c", cmd],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_cjson_repo() -> Path:
    CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
    if not (CACHE_DIR / ".git").is_dir():
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
        wsl_cache = _to_wsl_path(CACHE_DIR) if os.name == "nt" else str(CACHE_DIR)
        _run_linux_cmd(f"git clone --quiet {CJSON_REPO_URL} '{wsl_cache}'")
    return CACHE_DIR


def build_cjson_corpus() -> dict[str, Any]:
    repo_dir = ensure_cjson_repo()
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[dict[str, Any]] = []

    for ver in CJSON_VERSIONS:
        src_dir = CORPUS_DIR / ".build_cache" / f"cjson-{ver}"
        wsl_src = _to_wsl_path(src_dir) if os.name == "nt" else str(src_dir)
        _run_linux_cmd(f"rm -rf '{wsl_src}'")
        shutil.copytree(repo_dir, src_dir)
        _run_linux_cmd(f"git checkout --quiet v{ver}", cwd=src_dir)

        for variant_name, compiler, opt_flag in BUILD_VARIANTS:
            unstripped_name = f"libcjson-{ver}-{variant_name}-unstripped.so"
            stripped_name = f"libcjson-{ver}-{variant_name}-stripped.so"
            unstripped_path = BINARIES_DIR / unstripped_name
            stripped_path = BINARIES_DIR / stripped_name

            wsl_unstripped = (
                _to_wsl_path(unstripped_path) if os.name == "nt" else str(unstripped_path)
            )
            wsl_stripped = (
                _to_wsl_path(stripped_path) if os.name == "nt" else str(stripped_path)
            )

            compile_cmd = (
                f"{compiler} {opt_flag} -g -fPIC -shared "
                f"-Wl,-soname,libcjson.so.1 -o '{wsl_unstripped}' cJSON.c -lc"
            )
            _run_linux_cmd(compile_cmd, cwd=src_dir)

            strip_cmd = f"strip --strip-all -o '{wsl_stripped}' '{wsl_unstripped}'"
            _run_linux_cmd(strip_cmd, cwd=src_dir)

            manifest_entries.append(
                {
                    "filename": unstripped_name,
                    "version": ver,
                    "variant": variant_name,
                    "compiler": compiler,
                    "opt_flag": opt_flag,
                    "stripped": False,
                    "sha256": _sha256_file(unstripped_path),
                }
            )
            manifest_entries.append(
                {
                    "filename": stripped_name,
                    "version": ver,
                    "variant": variant_name,
                    "compiler": compiler,
                    "opt_flag": opt_flag,
                    "stripped": True,
                    "sha256": _sha256_file(stripped_path),
                }
            )

    manifest: dict[str, Any] = {
        "project": "cJSON Benchmark Corpus",
        "cve": CVE_ID,
        "patched_function": "cJSON_Minify",
        "versions": list(CJSON_VERSIONS),
        "binaries": manifest_entries,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    result = build_cjson_corpus()
    print(f"Built {len(result['binaries'])} cJSON binaries in {BINARIES_DIR}")
