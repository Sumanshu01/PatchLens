# PatchLens Part 1 — Known Static Analysis Limitations

This document catalogs the known architectural, disassembly, function boundary, and Control-Flow Graph (CFG) recovery limitations in **PatchLens Part 1**.

---

## 1. Architecture & Binary Format Scope

1. **Primary Architecture Support (`x86_64`)**:
   - Full recursive-descent, prologue heuristic discovery, PLT stub resolution, and PIC jump-table recovery are implemented and tuned for **64-bit x86-64 (`EM_X86_64`)** System V ABI ELF binaries.
   - `ARM64Profile` (`EM_AARCH64`) is provided as an extensible `ArchProfile` implementation with basic instruction classification and prologue matching (`paciasp`/`bti c`/`stp x29, x30`), but indirect jump-table slicing and PLT resolution are currently `x86_64`-specific.
   - 32-bit ELF (`EM_386`, `EM_ARM`), MIPS, PowerPC, and RISC-V binaries are not yet supported.
2. **Statically Linked & Heavily Packed/Obfuscated Binaries**:
   - The loader and disassembler assume standard compiler-emitted `.text`, `.rodata`, `.plt`/`.plt.sec` sections. Self-modifying code, runtime unpackers (e.g., UPX), encrypted sections, or binaries with stripped section headers (`e_shnum == 0`) are not supported.

---

## 2. Disassembly & Function Discovery in Stripped Binaries

1. **Indirect-Only Internal Functions Without Standard Prologues**:
   - In stripped binaries (`.symtab` removed), internal (`static`) functions are discovered via:
     1. Direct `call rel32` targets inside `.text`.
     2. `R_X86_64_RELATIVE` relocation addends in `.data.rel.ro`, `.init_array`, and `.fini_array` (which captures static functions referenced through dispatch tables such as `zlib`'s `configuration_table`).
     3. Linear-sweep gap scanning combined with `X86_64Profile.matches_prologue` (`endbr64`, `push rbp; mov rbp, rsp`, callee-saved register pushes, `sub rsp, imm`).
   - **Limitation**: If an internal static function is **never** called directly (`call rel32`), is **not** referenced by a relocation entry, **and** is a frameless leaf function lacking `endbr64`, register pushes, or stack allocation (e.g., a single `mov eax, edi; ret` compiled with `-fcf-protection=none -fomit-frame-pointer`), linear sweep will decode its instructions as part of the preceding function's range rather than creating a distinct function start.
2. **Tail-Call-Only Callees in Stripped Binaries**:
   - When Function A invokes static Function B exclusively via an unconditional `jmp rel32` (tail-call optimization at `-O2`/`-O3`) and Function B has no symbol in `.dynsym` and no direct `call` site, Phase 1 recursive descent treats `jmp rel32` as an intra-procedural branch rather than a call seed. If Function B is not separated by alignment padding and a recognized prologue during Phase 2, Function B can be merged into Function A's CFG.
3. **Cold/Hot Function Splitting (`-freorder-blocks-and-partition`)**:
   - When compilers split cold basic blocks into `.text.unlikely` (e.g., `foo.cold`), those fragments appear as separate symbols or outside the contiguous `[func_start, next_func_start)` range in `.text`. Part 1 treats jumps outside `[func_start, f_limit)` as tail transfers rather than stitching `.text.unlikely` fragments into the parent function's CFG.
4. **Overlapping Instructions & Inline Data in `.text`**:
   - x86-64 variable-length instruction encoding permits obfuscated binaries to jump into the middle of an already-decoded instruction. The recursive-descent engine rejects overlapping instruction decodes (`any(covered[off : off + insn.size])`) to avoid corrupting canonical compiler output.

---

## 3. Control-Flow Graph (CFG) & Indirect Branch Recovery

1. **Indirect Calls (`call rax`, `call qword ptr [rax + offset]`)**:
   - Indirect function calls through function pointers, C++ vtables, or callback structs (e.g., `strm->zalloc` and `strm->zfree` in `zlib`) cannot be statically resolved without inter-procedural value-set / points-to analysis. Their targets are not added to `Function.call_targets`.
2. **Jump Table Pattern Coverage**:
   - `resolve_jump_table` resolves standard GCC and Clang PIC 32-bit signed offset tables (`lea base, [rip + disp]` + scaled `*4` load + `add` + `[notrack] jmp reg`) and 64-bit absolute tables (`*8`), including cases where Loop-Invariant Code Motion (LICM) hoists the `lea` instruction to the function header.
   - **Limitations**:
     - Switch tables using shifted/byte-sized (`*1` or `*2`) relative offsets or multi-level decision trees combined with computed gotos may not match the pattern slicer.
     - If the compiler elides or separates the `cmp reg, imm` bounds check across distant basic blocks and no `.rodata` reference boundary immediately follows the table, table length heuristics may under- or over-approximate entries until the first non-`.text` / out-of-function offset is encountered.
     - When an indirect jump remains partially unresolved in a function, `recover_function_cfg` connects remaining unreached non-NOP blocks within the function's bounds to the closest preceding indirect jump block as a best-effort fallback so they are not lost, which can attach dead or exception-handler blocks to the switch dispatcher.
3. **Exception Handling & Non-Local Control Flow (`setjmp`/`longjmp`, C++ Exceptions)**:
   - `.eh_frame` / `.gcc_except_table` DWARF landing pads and `longjmp` transfers are not modeled as CFG edges.
4. **Non-Returning Function Heuristic**:
   - Calls to external non-returning functions are identified via a static allowlist (`abort`, `exit`, `_exit`, `__stack_chk_fail`, `__assert_fail`, `__cxa_throw`, `longjmp`, etc.). Custom internal `noreturn` functions in stripped binaries are treated as returning calls, which may introduce a spurious `FALLTHROUGH` edge to the following block.

