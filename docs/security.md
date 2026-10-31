# PatchLens Security Architecture & Threat Model

This document outlines the security architecture, sandboxing mechanisms, and threat model of **PatchLens** when parsing and diffing untrusted ELF binaries.

---

## 1. Threat Model & Security Posture

### The Primary Invariant: Zero Binary Execution
In reverse-engineering and patch analysis workflows, target binaries may originate from untrusted third parties, vulnerability disclosures, or potentially malicious submissions.

**PatchLens enforces a strict zero-execution policy:**
- Target ELF binaries are **never executed** (`execve`, `fork/exec`, `posix_spawn`, or shell subprocesses are strictly forbidden).
- Target shared libraries are **never dynamically loaded** (`dlopen`, `LoadLibrary`, or dynamic linker invocations are never used).
- Target binaries are treated purely as inert byte streams. All data extraction occurs via pure static analysis:
  1. ELF file headers, section headers, program headers, and symbol tables are parsed using `pyelftools`.
  2. Executable code sections (`.text`) are disassembled instruction-by-instruction using the Capstone engine in Python userspace.

---

## 2. Attack Vectors & Mitigations

### 2.1 Malicious ELF Header Parsing & Memory Corruption
- **Threat**: Crafted ELF headers designed to exploit parser vulnerabilities (e.g., integer overflows in section counts, corrupted string tables, circular relocation tables).
- **Mitigation**:
  - `pyelftools` is a pure-Python parser running in managed memory, eliminating memory corruption vulnerabilities (buffer overflows, use-after-free).
  - Explicit bounds and exception handling wrap all section lookups and virtual address translations (`LoadedELF.read_vaddr`). Corrupted headers raise `ELFParseError` and fail gracefully without crashing the server.

### 2.2 Disassembler Exploits & Infinite Loops
- **Threat**: Byte sequences designed to trigger disassembler crashes or infinite loops during recursive descent.
- **Mitigation**:
  - Disassembly is performed in Python via Capstone bindings with strict instruction size validation.
  - Recursive descent maintains a visited address set (`visited: set[int]`) preventing cycles and infinite recursion.
  - Linear sweep fallback only processes unvisited gaps within valid section bounds.

### 2.3 Resource Exhaustion (DoS)
- **Threat**: Bomb files (gigabyte-sized binaries) or deeply recursive graph topologies designed to exhaust memory or CPU.
- **Mitigation**:
  - **Upload Size Limit**: Strictly enforced pre-upload size check (`PATCHLENS_MAX_UPLOAD_MB`, default 50 MB). Files exceeding this threshold are immediately rejected with HTTP 413.
  - **Magic Bytes Validation**: Binary uploads must begin with standard ELF magic bytes (`\x7fELF`). Non-ELF payloads are rejected with HTTP 400.
  - **Execution Timeouts**: Background worker jobs enforce strict CPU time limits (`ANALYSIS_TIMEOUT_SECONDS`, default 180s).
  - **Memory Limits**: Analysis jobs run with memory tracking and lightweight data structures (slots, tuples) keeping peak analysis memory below 30 MB for realistic library binaries.

### 2.4 Path Traversal & Arbitrary File Overwrite
- **Threat**: Uploaded filenames containing path traversal sequences (`../../etc/passwd` or `C:\Windows\...`).
- **Mitigation**:
  - Uploaded filenames are sanitized: directory paths are stripped (`Path(filename).name`).
  - Files are persisted on disk using randomly generated UUID prefixes (`uuid4().hex + '_' + filename`) in a dedicated `uploads/` directory, preventing collisions or overwrites of existing system files.

---

## 3. Sandboxing & Process Isolation

```
+--------------------------------------------------------------+
|                      Client Browser                          |
+--------------------------------------------------------------+
                               |
                               v (HTTPS / WSS / REST)
+--------------------------------------------------------------+
|                 FastAPI Web Application                      |
|  - Magic byte verification (\x7fELF)                         |
|  - File size bounds checking (max 50 MB)                     |
|  - UUID file isolation                                       |
+--------------------------------------------------------------+
                               |
                               v (Job ID Enqueue)
+--------------------------------------------------------------+
|            Background Worker (Redis RQ / ProcessPool)        |
|  - Subprocess isolation                                      |
|  - CPU timeout bounds (180s)                                 |
|  - Non-root user privileges (Docker)                         |
|  - Inert static byte parsing only                            |
|  - No network egress permitted during analysis               |
+--------------------------------------------------------------+
```

1. **Docker Container Hardening**:
   - The API and Worker containers run as non-root unprivileged users (`appuser:10001`).
   - Read-only container root filesystems with ephemeral scratch volumes for uploads.
   - Capability drops (`cap_drop: ALL`) preventing privilege escalation.
2. **Network Isolation**:
   - Worker processes require no outbound internet access during analysis; all parsing is local and offline.

