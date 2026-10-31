"""Download and compile zlib 1.2.11 and 1.2.12 corpus binaries and derive ground truth."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

CORPUS_DIR = Path(__file__).resolve().parent
BINARIES_DIR = CORPUS_DIR / "binaries"
GROUND_TRUTH_DIR = CORPUS_DIR / "ground_truth"
CACHE_DIR = CORPUS_DIR / ".build_cache"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"

ZLIB_REPO_URL = "https://github.com/madler/zlib.git"
ZLIB_VERSIONS: tuple[str, ...] = ("1.2.11", "1.2.12")
CVE_COMMIT_SHA = "5c44459c3b28a9bd3283aaceab7c615f8020c531"

# Standard 15 core C translation units that make up libz.so in zlib's Makefile.in
ZLIB_CORE_SOURCES: tuple[str, ...] = (
    "adler32.c",
    "compress.c",
    "crc32.c",
    "deflate.c",
    "gzclose.c",
    "gzlib.c",
    "gzread.c",
    "gzwrite.c",
    "infback.c",
    "inffast.c",
    "inflate.c",
    "inftrees.c",
    "trees.c",
    "uncompr.c",
    "zutil.c",
)

BUILD_VARIANTS: tuple[tuple[str, str, str], ...] = (
    ("gcc-O0", "gcc", "-O0"),
    ("gcc-O2", "gcc", "-O2"),
    ("gcc-O3", "gcc", "-O3"),
    ("clang-O2", "clang", "-O2"),
)


def _to_wsl_path(win_path: Path) -> str:
    """Convert a Windows filesystem path to a `/mnt/<drive>/...` WSL path."""
    resolved = win_path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", 1)[-1].lstrip("/")
    return f"/mnt/{drive}/{tail}"


def _run_linux_cmd(cmd: str, cwd: Path | None = None) -> str:
    """Execute a shell command natively on Linux or inside WSL on Windows."""
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
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_zlib_repo() -> Path:
    """Clone or update the upstream madler/zlib git repository in CACHE_DIR."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    repo_dir = CACHE_DIR / "zlib-git"
    if not (repo_dir / ".git").is_dir():
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        subprocess.run(
            ["git", "clone", "--quiet", ZLIB_REPO_URL, str(repo_dir)],
            check=True,
        )
    return repo_dir


def _extract_c_function_spans(source_text: str) -> list[tuple[str, int, int]]:
    """Parse C source file to map function definitions to (func_name, start_line, end_line)."""
    lines = source_text.splitlines()
    spans: list[tuple[str, int, int]] = []
    # Match C function headers in zlib (both ANSI and K&R style used in zlib 1.2.11/1.2.12)
    ident_re = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    control_keywords = {
        "if",
        "for",
        "while",
        "switch",
        "return",
        "sizeof",
        "defined",
        "typeof",
        "ZEXPORT",
        "ZEXTERN",
        "OF",
    }

    idx = 0
    total = len(lines)
    while idx < total:
        line = lines[idx]
        stripped = line.strip()
        # Function definitions in zlib start at column 0 (or after storage class / return type)
        if not stripped or stripped.startswith(
            ("#", "//", "/*", "*", "typedef", "struct", "union", "enum")
        ):
            idx += 1
            continue

        # Look for top-level opening brace `{` of a function body
        if not line.startswith((" ", "\t")) and "(" in line:
            header_start = idx
            header_lines = [line]
            scan = idx + 1
            while scan < total and scan <= idx + 12:
                if "{" in lines[scan - 1]:
                    break
                if ";" in lines[scan - 1] and ")" in lines[scan - 1]:
                    # Prototype or global declaration, not a function definition with K&R args
                    # Wait: K&R declarations have `;` AFTER `)` and before `{`!
                    pass
                header_lines.append(lines[scan])
                if "{" in lines[scan]:
                    scan += 1
                    break
                if lines[scan].strip().startswith("#"):
                    break
                scan += 1

            combined_header = " ".join(header_lines)
            if "{" in combined_header and "=" not in combined_header.split("{")[0]:
                before_brace = combined_header.split("{")[0]
                # Find the function name before the first parameter list `(`
                candidates = [
                    m.group(1)
                    for m in ident_re.finditer(before_brace)
                    if m.group(1) not in control_keywords
                ]
                if candidates:
                    func_name = candidates[0]
                    # Trace brace depth to find function end line
                    brace_depth = 0
                    body_end = header_start
                    found_open = False
                    for b_idx in range(header_start, total):
                        for ch in lines[b_idx]:
                            if ch == "{":
                                brace_depth += 1
                                found_open = True
                            elif ch == "}":
                                brace_depth -= 1
                        if found_open and brace_depth <= 0:
                            body_end = b_idx + 1
                            break
                    if body_end > header_start:
                        spans.append((func_name, header_start + 1, body_end))
                        idx = body_end
                        continue
        idx += 1
    return spans


def _parse_diff_modified_functions(
    repo_dir: Path,
    base_rev: str,
    target_rev: str,
) -> dict[str, list[str]]:
    """Derive modified C functions per file between `base_rev` and `target_rev` from git diff."""
    diff_out = subprocess.run(
        ["git", "diff", "-U0", base_rev, target_rev, "--", *ZLIB_CORE_SOURCES],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    current_file: str | None = None
    changed_lines_old: dict[str, set[int]] = {}
    changed_lines_new: dict[str, set[int]] = {}

    for line in diff_out.splitlines():
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            current_file = line[6:].strip()
        elif line.startswith("@@ ") and current_file in ZLIB_CORE_SOURCES:
            m = hunk_re.match(line)
            if m:
                old_start = int(m.group(1))
                old_count = int(m.group(2)) if m.group(2) is not None else 1
                new_start = int(m.group(3))
                new_count = int(m.group(4)) if m.group(4) is not None else 1
                old_set = changed_lines_old.setdefault(current_file, set())
                new_set = changed_lines_new.setdefault(current_file, set())
                for ln in range(old_start, old_start + max(old_count, 1)):
                    old_set.add(ln)
                for ln in range(new_start, new_start + max(new_count, 1)):
                    new_set.add(ln)

    modified_by_file: dict[str, list[str]] = {}
    for src_file in sorted(set(changed_lines_old.keys()) | set(changed_lines_new.keys())):
        old_src = subprocess.run(
            ["git", "show", f"{base_rev}:{src_file}"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        new_src = subprocess.run(
            ["git", "show", f"{target_rev}:{src_file}"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

        old_spans = _extract_c_function_spans(old_src)
        new_spans = _extract_c_function_spans(new_src)

        funcs: set[str] = set()
        for f_name, s_line, e_line in old_spans:
            if any(s_line <= ln <= e_line for ln in changed_lines_old.get(src_file, set())):
                funcs.add(f_name)
        for f_name, s_line, e_line in new_spans:
            if any(s_line <= ln <= e_line for ln in changed_lines_new.get(src_file, set())):
                funcs.add(f_name)

        if funcs:
            modified_by_file[src_file] = sorted(funcs)

    return modified_by_file


def generate_ground_truth(repo_dir: Path) -> dict[str, Any]:
    """Derive ground truth from upstream git commits and write corpus/ground_truth/."""
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    cve_commit_msg = subprocess.run(
        ["git", "log", "-1", "--format=%B", CVE_COMMIT_SHA],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    cve_modified = _parse_diff_modified_functions(repo_dir, f"{CVE_COMMIT_SHA}~1", CVE_COMMIT_SHA)
    release_modified = _parse_diff_modified_functions(repo_dir, "v1.2.11", "v1.2.12")

    all_cve_funcs = sorted({fn for fn_list in cve_modified.values() for fn in fn_list})
    all_release_funcs = sorted({fn for fn_list in release_modified.values() for fn in fn_list})

    ground_truth_data: dict[str, Any] = {
        "cve_id": "CVE-2018-25032",
        "upstream_repository": ZLIB_REPO_URL,
        "base_version": "1.2.11",
        "patched_version": "1.2.12",
        "security_fix_commit": {
            "sha": CVE_COMMIT_SHA,
            "message": cve_commit_msg,
            "modified_functions_by_file": cve_modified,
            "modified_functions": all_cve_funcs,
        },
        "full_release_diff_v1_2_11_to_v1_2_12": {
            "from_tag": "v1.2.11",
            "to_tag": "v1.2.12",
            "modified_functions_by_file": release_modified,
            "modified_functions": all_release_funcs,
        },
    }

    gt_json_path = GROUND_TRUTH_DIR / "cve_2018_25032.json"
    gt_json_path.write_text(
        json.dumps(ground_truth_data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    gt_readme_lines = [
        "# Ground Truth: zlib 1.2.11 -> 1.2.12 (CVE-2018-25032)",
        "",
        "Derived directly from the upstream `madler/zlib` Git repository.",
        "",
        "## Security Fix Commit (`5c44459c3b28a9bd3283aaceab7c615f8020c531`)",
        "",
        f"> {cve_commit_msg}",
        "",
        "### Functions Modified in CVE-2018-25032 Fix Commit",
        "",
    ]
    for src_file, fn_list in sorted(cve_modified.items()):
        gt_readme_lines.append(f"- **`{src_file}`**: {', '.join(f'`{f}`' for f in fn_list)}")

    gt_readme_lines.extend(
        [
            "",
            "## Full Release Diff (`v1.2.11` .. `v1.2.12`)",
            "",
            "All core library functions modified across the entire `1.2.11 -> 1.2.12` release:",
            "",
        ]
    )
    for src_file, fn_list in sorted(release_modified.items()):
        gt_readme_lines.append(f"- **`{src_file}`**: {', '.join(f'`{f}`' for f in fn_list)}")

    (GROUND_TRUTH_DIR / "README.md").write_text(
        "\n".join(gt_readme_lines) + "\n",
        encoding="utf-8",
    )
    return ground_truth_data


def build_corpus() -> dict[str, Any]:
    """Compile all 16 zlib shared library variants and record manifest.json."""
    repo_dir = ensure_zlib_repo()
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)

    gcc_version = _run_linux_cmd("gcc --version | head -n 1").strip()
    clang_version = _run_linux_cmd("clang --version | head -n 1").strip()

    manifest_entries: list[dict[str, Any]] = []
    common_cflags = (
        "-std=gnu11 -Wno-deprecated-non-prototype "
        "-fPIC -shared -D_LARGEFILE64_SOURCE=1 -DHAVE_HIDDEN -DZLIB_INTERNAL"
    )

    for version in ZLIB_VERSIONS:
        src_dir = CACHE_DIR / f"zlib-{version}"
        if src_dir.exists():
            shutil.rmtree(src_dir)
        shutil.copytree(repo_dir, src_dir)
        subprocess.run(
            ["git", "checkout", "--quiet", f"v{version}"],
            cwd=src_dir,
            check=True,
        )

        src_files_str = " ".join(ZLIB_CORE_SOURCES)
        for variant_name, compiler, opt_flag in BUILD_VARIANTS:
            unstripped_name = f"libz-{version}-{variant_name}-unstripped.so"
            stripped_name = f"libz-{version}-{variant_name}-stripped.so"
            unstripped_path = BINARIES_DIR / unstripped_name
            stripped_path = BINARIES_DIR / stripped_name

            wsl_unstripped = (
                _to_wsl_path(unstripped_path) if os.name == "nt" else str(unstripped_path)
            )
            wsl_stripped = _to_wsl_path(stripped_path) if os.name == "nt" else str(stripped_path)

            compile_cmd = (
                f"{compiler} {opt_flag} -g {common_cflags} "
                f"-Wl,-soname,libz.so.1 -o {unstripped_name} {src_files_str} -lc"
            )
            actual_exec_cmd = (
                f"{compiler} {opt_flag} -g {common_cflags} "
                f"-Wl,-soname,libz.so.1 -o '{wsl_unstripped}' {src_files_str} -lc"
            )
            _run_linux_cmd(actual_exec_cmd, cwd=src_dir)

            strip_cmd = f"strip --strip-all -o {stripped_name} {unstripped_name}"
            actual_strip_cmd = f"strip --strip-all -o '{wsl_stripped}' '{wsl_unstripped}'"
            _run_linux_cmd(actual_strip_cmd, cwd=src_dir)

            manifest_entries.append(
                {
                    "filename": unstripped_name,
                    "relative_path": f"corpus/binaries/{unstripped_name}",
                    "version": version,
                    "variant": variant_name,
                    "compiler": compiler,
                    "opt_flag": opt_flag,
                    "stripped": False,
                    "build_command": compile_cmd,
                    "sha256": _sha256_file(unstripped_path),
                    "size_bytes": unstripped_path.stat().st_size,
                }
            )
            manifest_entries.append(
                {
                    "filename": stripped_name,
                    "relative_path": f"corpus/binaries/{stripped_name}",
                    "version": version,
                    "variant": variant_name,
                    "compiler": compiler,
                    "opt_flag": opt_flag,
                    "stripped": True,
                    "build_command": f"{compile_cmd} && {strip_cmd}",
                    "sha256": _sha256_file(stripped_path),
                    "size_bytes": stripped_path.stat().st_size,
                }
            )

    ground_truth = generate_ground_truth(repo_dir)

    manifest: dict[str, Any] = {
        "project": "PatchLens Benchmark Corpus",
        "target": "zlib",
        "versions": list(ZLIB_VERSIONS),
        "cve": "CVE-2018-25032",
        "toolchain": {
            "gcc": gcc_version,
            "clang": clang_version,
        },
        "binaries": manifest_entries,
        "ground_truth_file": "corpus/ground_truth/cve_2018_25032.json",
        "cve_modified_functions": ground_truth["security_fix_commit"]["modified_functions"],
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    result = build_corpus()
    print(f"Built {len(result['binaries'])} ELF shared libraries in {BINARIES_DIR}")
    print(f"Manifest written to {MANIFEST_PATH}")
