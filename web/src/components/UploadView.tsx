import React, { useEffect, useState } from "react";
import {
  UploadCloud,
  FileCode2,
  Sparkles,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { SampleCase } from "../types";
import { getSampleCases, uploadBinary, startAnalysis } from "../api";

interface UploadViewProps {
  onAnalysisStarted: (jobId: string) => void;
  onSampleSelected: (resultId: number) => void;
}

export const UploadView: React.FC<UploadViewProps> = ({
  onAnalysisStarted,
  onSampleSelected,
}) => {
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [samples, setSamples] = useState<SampleCase[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-typing prompt state (just like Landing Page)
  const patchPrompts = [
    "Locate CVE-2018-25032 deflate buffer vulnerability in stripped zlib.so",
    "Diff cJSON 1.7.12 vs 1.7.14 to isolate CVE-2019-1010239 bounds check fix",
    "Match basic-block CFG fingerprints across O2 and O3 binaries",
    "Rank patched functions by cyclomatic complexity and guard additions",
  ];
  const [promptIdx, setPromptIdx] = useState(0);
  const [promptText, setPromptText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    getSampleCases()
      .then(setSamples)
      .catch((err) => console.error("Could not fetch samples:", err));
  }, []);

  // Auto-typing prompt effect
  useEffect(() => {
    const current = patchPrompts[promptIdx];
    let timer: ReturnType<typeof setTimeout>;

    if (!isDeleting) {
      if (promptText.length < current.length) {
        timer = setTimeout(() => {
          setPromptText(current.slice(0, promptText.length + 1));
        }, 34);
      } else {
        timer = setTimeout(() => {
          setIsDeleting(true);
        }, 2600);
      }
    } else {
      if (promptText.length > 0) {
        timer = setTimeout(() => {
          setPromptText(current.slice(0, Math.max(0, promptText.length - 2)));
        }, 14);
      } else {
        setIsDeleting(false);
        setPromptIdx((prev) => (prev + 1) % patchPrompts.length);
        timer = setTimeout(() => {}, 250);
      }
    }

    return () => clearTimeout(timer);
  }, [promptText, isDeleting, promptIdx]);

  const validateElfFile = async (file: File): Promise<string | null> => {
    if (file.size > 50 * 1024 * 1024) {
      return `File ${file.name} exceeds 50MB maximum size limit.`;
    }
    const headerBuf = await file.slice(0, 4).arrayBuffer();
    const bytes = new Uint8Array(headerBuf);
    if (
      bytes.length < 4 ||
      bytes[0] !== 0x7f ||
      bytes[1] !== 0x45 ||
      bytes[2] !== 0x4c ||
      bytes[3] !== 0x46
    ) {
      return `File ${file.name} is not a valid ELF binary (missing \\x7fELF header).`;
    }
    return null;
  };

  const handleFileDrop = async (
    e: React.DragEvent<HTMLDivElement>,
    target: "A" | "B"
  ) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const err = await validateElfFile(file);
      if (err) {
        setError(err);
        return;
      }
      setError(null);
      if (target === "A") setFileA(file);
      else setFileB(file);
    }
  };

  const handleFileInput = async (
    e: React.ChangeEvent<HTMLInputElement>,
    target: "A" | "B"
  ) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const err = await validateElfFile(file);
      if (err) {
        setError(err);
        return;
      }
      setError(null);
      if (target === "A") setFileA(file);
      else setFileB(file);
    }
  };

  const handleSubmit = async () => {
    if (!fileA || !fileB) return;
    setIsUploading(true);
    setError(null);

    try {
      const [upA, upB] = await Promise.all([
        uploadBinary(fileA),
        uploadBinary(fileB),
      ]);

      const job = await startAnalysis(upA.id, upB.id);
      onAnalysisStarted(job.job_id);
    } catch (err: any) {
      setError(err.message || "Failed to start analysis");
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
      {/* Top Interactive Patch Prompt Box with Tab & Corner Brackets */}
      <div className="relative mb-8 max-w-3xl mx-auto">
        <div className="w-10 h-10 border border-b-0 border-stone-900/20 bg-[#efece6] flex items-center justify-center font-serif text-2xl font-bold leading-none text-slate-900">
          “
        </div>
        <div className="relative p-4 sm:p-5 border border-stone-900/30 bg-[#efece6]/95 backdrop-blur-xs font-mono text-[11px] sm:text-xs uppercase tracking-wide leading-relaxed text-slate-800 min-h-[82px] shadow-xs">
          {/* 4 Corner Brackets */}
          <div className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-slate-900" />
          <div className="absolute -top-1 -right-1 w-2 h-2 border-t border-r border-slate-900" />
          <div className="absolute -bottom-1 -left-1 w-2 h-2 border-b border-l border-slate-900" />
          <div className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-slate-900" />

          <span className="text-slate-900">{promptText}</span>
          <span className="inline-block w-1.5 h-3 bg-slate-900 align-middle ml-1 animate-pulse" />
        </div>
      </div>

      {/* Hero Header */}
      <div className="text-center mb-10">
        <div className="font-mono text-xs uppercase tracking-widest text-indigo-700 mb-3 font-semibold">
          UNLEASH THE POWER OF AUTOMATED DIFFING
        </div>

        <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-white/90 border border-stone-300 text-indigo-700 mb-5 shadow-2xs backdrop-blur-xs">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
          <span>Automated 1-Day Vulnerability Patch Localization</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-slate-900 leading-[1.08] mb-5">
          Pinpoint Security Patches in{" "}
          <span className="relative inline-block px-3 py-0.5 mt-1 bg-white/80 border border-stone-300 rounded-lg text-indigo-700 shadow-2xs">
            Stripped Binaries
          </span>
        </h1>

        <p className="text-sm sm:text-base text-slate-700 max-w-2xl mx-auto leading-relaxed bg-[#efece6]/85 backdrop-blur-xs p-3.5 rounded-xl border border-stone-900/10">
          Upload baseline and patched ELF executables or shared libraries. PatchLens disassembles
          the control-flow topology, normalizes compiler noise, and isolates security fixes.
        </p>
      </div>

      {/* Quick Sample Selector Card */}
      <div className="relative mb-10 p-6 rounded-2xl bg-white/90 border border-slate-900/40 shadow-[3px_3px_0px_#141414] backdrop-blur-xs">
        {/* 4 Corner Brackets */}
        <span className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-slate-900" />
        <span className="absolute -top-1 -right-1 w-2 h-2 border-t border-r border-slate-900" />
        <span className="absolute -bottom-1 -left-1 w-2 h-2 border-b border-l border-slate-900" />
        <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-slate-900" />

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-5">
          <div>
            <div className="flex items-center space-x-2.5">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <h2 className="text-sm font-bold text-slate-900 uppercase font-mono tracking-wider">
                Try a Pre-computed Sample Case
              </h2>
              <span className="text-[10px] font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-300">
                INSTANT (&lt;1s)
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-1 font-mono">
              Instantly explore real CVE security diffs with zero build or upload delay.
            </p>
          </div>

          <div className="flex flex-wrap gap-2.5">
            {samples.map((s) => (
              <button
                key={s.id}
                onClick={() => s.result_id && onSampleSelected(s.result_id)}
                disabled={!s.result_id}
                className="group relative inline-flex items-center space-x-2 px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-slate-900 border border-slate-900 bg-white hover:bg-stone-50 shadow-[2px_2px_0px_#141414] hover:shadow-[3px_3px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all cursor-pointer select-none"
              >
                {/* 4 Maximalist Technical Corner Brackets */}
                <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
                <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
                <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
                <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />

                <span>{s.title}</span>
                <ArrowRight className="w-3.5 h-3.5 text-indigo-700 group-hover:translate-x-0.5 transition-transform" />
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-8 p-4 rounded-xl bg-rose-50 border border-rose-300 flex items-start space-x-3 text-rose-900 text-xs shadow-[2px_2px_0px_#141414]">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
          <span className="font-mono">{error}</span>
        </div>
      )}

      {/* Dual Upload Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
        {/* Binary A: Baseline */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => handleFileDrop(e, "A")}
          className={`relative p-6 sm:p-8 rounded-2xl border transition-all ${
            fileA
              ? "border-slate-900 bg-indigo-50/40 shadow-[3px_3px_0px_#141414]"
              : "border-stone-900/30 hover:border-slate-900 bg-white/90 hover:bg-white shadow-[2px_2px_0px_#141414]"
          }`}
        >
          {/* Corner Brackets */}
          <span className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-slate-900" />
          <span className="absolute -top-1 -right-1 w-2 h-2 border-t border-r border-slate-900" />
          <span className="absolute -bottom-1 -left-1 w-2 h-2 border-b border-l border-slate-900" />
          <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-slate-900" />

          {/* Header strip */}
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-stone-200">
            <span className="font-mono text-xs font-bold uppercase text-slate-800 tracking-wider">
              // TARGET 01: BASELINE
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-stone-100 text-slate-700 border border-stone-300">
              OLD / VULNERABLE
            </span>
          </div>

          <input
            type="file"
            id="file-a-input"
            onChange={(e) => handleFileInput(e, "A")}
            className="hidden"
          />
          <label htmlFor="file-a-input" className="cursor-pointer block text-center py-4">
            <div className="w-12 h-12 mx-auto rounded-xl bg-stone-100 border border-stone-300 flex items-center justify-center text-slate-600 mb-4 shadow-2xs">
              {fileA ? (
                <FileCode2 className="w-6 h-6 text-indigo-700" />
              ) : (
                <UploadCloud className="w-6 h-6 text-slate-500" />
              )}
            </div>
            <h3 className="font-bold text-sm text-slate-900">
              {fileA ? fileA.name : "1. Baseline Binary (Old / Vulnerable)"}
            </h3>
            <p className="text-xs text-slate-500 mt-1 font-mono">
              {fileA
                ? `${(fileA.size / 1024).toFixed(1)} KB`
                : "Drop ELF shared library or executable (.so, .elf)"}
            </p>

            {fileA ? (
              <div className="mt-4 inline-flex items-center space-x-1.5 px-3 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-300 text-xs font-mono font-bold">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>ELF BINARY READY</span>
              </div>
            ) : (
              <span className="mt-4 inline-block font-mono text-xs uppercase font-bold text-indigo-700 hover:underline">
                Browse Files
              </span>
            )}
          </label>
        </div>

        {/* Binary B: Patched */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => handleFileDrop(e, "B")}
          className={`relative p-6 sm:p-8 rounded-2xl border transition-all ${
            fileB
              ? "border-slate-900 bg-indigo-50/40 shadow-[3px_3px_0px_#141414]"
              : "border-stone-900/30 hover:border-slate-900 bg-white/90 hover:bg-white shadow-[2px_2px_0px_#141414]"
          }`}
        >
          {/* Corner Brackets */}
          <span className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-slate-900" />
          <span className="absolute -top-1 -right-1 w-2 h-2 border-t border-r border-slate-900" />
          <span className="absolute -bottom-1 -left-1 w-2 h-2 border-b border-l border-slate-900" />
          <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-slate-900" />

          {/* Header strip */}
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-stone-200">
            <span className="font-mono text-xs font-bold uppercase text-slate-800 tracking-wider">
              // TARGET 02: PATCHED
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-stone-100 text-slate-700 border border-stone-300">
              NEW / FIXED
            </span>
          </div>

          <input
            type="file"
            id="file-b-input"
            onChange={(e) => handleFileInput(e, "B")}
            className="hidden"
          />
          <label htmlFor="file-b-input" className="cursor-pointer block text-center py-4">
            <div className="w-12 h-12 mx-auto rounded-xl bg-stone-100 border border-stone-300 flex items-center justify-center text-slate-600 mb-4 shadow-2xs">
              {fileB ? (
                <FileCode2 className="w-6 h-6 text-indigo-700" />
              ) : (
                <UploadCloud className="w-6 h-6 text-slate-500" />
              )}
            </div>
            <h3 className="font-bold text-sm text-slate-900">
              {fileB ? fileB.name : "2. Patched Binary (New / Fixed)"}
            </h3>
            <p className="text-xs text-slate-500 mt-1 font-mono">
              {fileB
                ? `${(fileB.size / 1024).toFixed(1)} KB`
                : "Drop ELF shared library or executable (.so, .elf)"}
            </p>

            {fileB ? (
              <div className="mt-4 inline-flex items-center space-x-1.5 px-3 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-300 text-xs font-mono font-bold">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>ELF BINARY READY</span>
              </div>
            ) : (
              <span className="mt-4 inline-block font-mono text-xs uppercase font-bold text-indigo-700 hover:underline">
                Browse Files
              </span>
            )}
          </label>
        </div>
      </div>

      {/* Start Button */}
      <div className="text-center mb-16">
        <button
          onClick={handleSubmit}
          disabled={!fileA || !fileB || isUploading}
          className={`group relative inline-flex items-center justify-center space-x-3 px-10 py-4 font-mono text-sm font-black uppercase tracking-wider border border-slate-900 transition-all ${
            fileA && fileB && !isUploading
              ? "bg-slate-900 text-white hover:bg-indigo-700 shadow-[3px_3px_0px_#141414] hover:shadow-[4px_4px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none cursor-pointer"
              : "bg-stone-200 text-stone-400 border-stone-300 cursor-not-allowed shadow-none"
          }`}
        >
          {/* 4 Corner Brackets */}
          <span className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-slate-900 pointer-events-none" />
          <span className="absolute -top-1 -right-1 w-2 h-2 border-t border-r border-slate-900 pointer-events-none" />
          <span className="absolute -bottom-1 -left-1 w-2 h-2 border-b border-l border-slate-900 pointer-events-none" />
          <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-slate-900 pointer-events-none" />

          {/* Gradient accent clip */}
          <div className="absolute inset-[-1px] pointer-events-none [clip-path:polygon(0_0,45%_0,45%_2px,2px_2px,2px_100%,0_100%)] bg-gradient-to-br from-[#ffb347] via-[#ff5a5f] to-[#ff3d8b]" />

          <span>{isUploading ? "Uploading & Initializing Engine..." : "•• Start Binary Diff Analysis"}</span>
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>

      {/* Quick Stat Pill Grid (Matching Landing Page Style) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16">
        <div className="p-4 rounded-xl bg-white/90 backdrop-blur-xs border border-stone-300 shadow-xs relative">
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
            Matching Accuracy
          </span>
          <span className="text-xl font-black text-indigo-700 font-mono mt-0.5 block">0.9923 F1</span>
          <span className="text-xs text-slate-500 mt-0.5 block">Stripped same-opt</span>
        </div>
        <div className="p-4 rounded-xl bg-white/90 backdrop-blur-xs border border-stone-300 shadow-xs relative">
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
            cJSON CVE-2019-1010239
          </span>
          <span className="text-xl font-black text-emerald-700 font-mono mt-0.5 block">100% Top-1</span>
          <span className="text-xs text-slate-500 mt-0.5 block">All 6 build variants</span>
        </div>
        <div className="p-4 rounded-xl bg-white/90 backdrop-blur-xs border border-stone-300 shadow-xs relative">
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
            zlib CVE-2018-25032
          </span>
          <span className="text-xl font-black text-indigo-700 font-mono mt-0.5 block">100% Top-10</span>
          <span className="text-xs text-slate-500 mt-0.5 block">All 8 build variants</span>
        </div>
        <div className="p-4 rounded-xl bg-white/90 backdrop-blur-xs border border-stone-300 shadow-xs relative">
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
            Noise Reduction
          </span>
          <span className="text-xl font-black text-rose-700 font-mono mt-0.5 block">99.8% Filter</span>
          <span className="text-xs text-slate-500 mt-0.5 block">30k diff lines to 54 funcs</span>
        </div>
      </div>

      {/* 4-Step Analysis Pipeline Grid */}
      <div className="border-t border-stone-900/10 pt-10">
        <div className="text-center mb-8">
          <span className="font-mono text-xs font-bold text-indigo-700 uppercase tracking-widest">
            ANALYSIS ARCHITECTURE
          </span>
          <h3 className="text-xl font-extrabold text-slate-900 mt-1">
            Engine Processing Ladder
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="p-5 rounded-2xl bg-white/90 border border-stone-300 shadow-xs relative">
            <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono text-xs font-bold flex items-center justify-center mb-3">
              01
            </div>
            <h4 className="text-sm font-bold text-slate-900">ELF Ingestion</h4>
            <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
              Safely extracts headers, segments, dynamic imports, and exported symbols.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white/90 border border-stone-300 shadow-xs relative">
            <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono text-xs font-bold flex items-center justify-center mb-3">
              02
            </div>
            <h4 className="text-sm font-bold text-slate-900">Graph Invariants</h4>
            <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
              Capstone disassembles functions, recovering basic blocks and jump edges.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white/90 border border-stone-300 shadow-xs relative">
            <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono text-xs font-bold flex items-center justify-center mb-3">
              03
            </div>
            <h4 className="text-sm font-bold text-slate-900">Multi-Pass Matching</h4>
            <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
              Weisfeiler-Lehman kernels match structural topologies across compilers.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white/90 border border-stone-300 shadow-xs relative">
            <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono text-xs font-bold flex items-center justify-center mb-3">
              04
            </div>
            <h4 className="text-sm font-bold text-slate-900">Semantic Diffing</h4>
            <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
              Scans for security check patterns (bounds guards, NULL checks, return logic).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
