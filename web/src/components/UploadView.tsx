import React, { useEffect, useState } from "react";
import { UploadCloud, FileCode2, Sparkles, AlertCircle, ArrowRight } from "lucide-react";
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

  useEffect(() => {
    getSampleCases()
      .then(setSamples)
      .catch((err) => console.error("Could not fetch samples:", err));
  }, []);

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
    <div className="max-w-5xl mx-auto py-12 px-4 sm:px-6">
      {/* Hero Header */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
          Pinpoint Security Patches in{" "}
          <span className="text-indigo-700 bg-gradient-to-r from-indigo-700 via-indigo-600 to-blue-700 bg-clip-text text-transparent">
            Stripped Binaries
          </span>
        </h1>
        <p className="mt-4 text-base sm:text-lg text-slate-600 max-w-2xl mx-auto">
          High-precision binary diffing powered by Weisfeiler-Lehman graph
          kernels, BinDiff MD-Index, and automated security patch heuristics.
        </p>
      </div>

      {/* Quick Sample Selector */}
      <div className="mb-10 p-6 rounded-2xl bg-gradient-to-r from-indigo-50/70 via-white to-stone-50 border border-indigo-100 shadow-xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <h2 className="text-sm font-bold text-slate-900">
                Try a Pre-computed Sample Case
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                Instant (<span className="tabular-nums">&lt;1s</span>)
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Explore real CVE security diffs with zero build or upload delay.
            </p>
          </div>

          <div className="flex flex-wrap gap-2.5">
            {samples.map((s) => (
              <button
                key={s.id}
                onClick={() => s.result_id && onSampleSelected(s.result_id)}
                disabled={!s.result_id}
                className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white text-slate-800 border border-stone-200 hover:border-indigo-300 hover:bg-indigo-50/40 shadow-2xs hover:shadow-xs transition-all active:scale-95 cursor-pointer"
              >
                <span>{s.title}</span>
                <ArrowRight className="w-3.5 h-3.5 text-indigo-600" />
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-3 text-rose-800 text-sm shadow-xs">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Dual Upload Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Binary A: Baseline */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => handleFileDrop(e, "A")}
          className={`relative border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center transition-all ${
            fileA
              ? "border-indigo-500 bg-indigo-50/30 shadow-xs"
              : "border-stone-300 hover:border-indigo-400 bg-white hover:bg-stone-50/50 shadow-xs"
          }`}
        >
          <input
            type="file"
            id="file-a-input"
            onChange={(e) => handleFileInput(e, "A")}
            className="hidden"
          />
          <label htmlFor="file-a-input" className="cursor-pointer block">
            <div className="w-12 h-12 mx-auto rounded-full bg-stone-100 flex items-center justify-center text-slate-500 mb-4">
              {fileA ? (
                <FileCode2 className="w-6 h-6 text-indigo-700" />
              ) : (
                <UploadCloud className="w-6 h-6 text-slate-400" />
              )}
            </div>
            <h3 className="font-bold text-sm text-slate-900">
              {fileA ? fileA.name : "1. Baseline Binary (Old / Vulnerable)"}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              {fileA
                ? `${(fileA.size / 1024).toFixed(1)} KB`
                : "Drop ELF shared library or executable (.so, .elf)"}
            </p>
            <span className="mt-4 inline-block text-xs font-semibold text-indigo-700 hover:text-indigo-800">
              {fileA ? "Click to change" : "Browse files"}
            </span>
          </label>
        </div>

        {/* Binary B: Patched */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => handleFileDrop(e, "B")}
          className={`relative border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center transition-all ${
            fileB
              ? "border-indigo-500 bg-indigo-50/30 shadow-xs"
              : "border-stone-300 hover:border-indigo-400 bg-white hover:bg-stone-50/50 shadow-xs"
          }`}
        >
          <input
            type="file"
            id="file-b-input"
            onChange={(e) => handleFileInput(e, "B")}
            className="hidden"
          />
          <label htmlFor="file-b-input" className="cursor-pointer block">
            <div className="w-12 h-12 mx-auto rounded-full bg-stone-100 flex items-center justify-center text-slate-500 mb-4">
              {fileB ? (
                <FileCode2 className="w-6 h-6 text-indigo-700" />
              ) : (
                <UploadCloud className="w-6 h-6 text-slate-400" />
              )}
            </div>
            <h3 className="font-bold text-sm text-slate-900">
              {fileB ? fileB.name : "2. Patched Binary (New / Fixed)"}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              {fileB
                ? `${(fileB.size / 1024).toFixed(1)} KB`
                : "Drop ELF shared library or executable (.so, .elf)"}
            </p>
            <span className="mt-4 inline-block text-xs font-semibold text-indigo-700 hover:text-indigo-800">
              {fileB ? "Click to change" : "Browse files"}
            </span>
          </label>
        </div>
      </div>

      {/* Start Button */}
      <div className="text-center">
        <button
          onClick={handleSubmit}
          disabled={!fileA || !fileB || isUploading}
          className={`px-8 py-3.5 rounded-xl font-bold text-sm shadow-md transition-all ${
            fileA && fileB && !isUploading
              ? "bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20 hover:shadow-lg hover:shadow-indigo-600/25 hover:-translate-y-0.5 active:scale-95 cursor-pointer"
              : "bg-stone-200 text-stone-400 cursor-not-allowed shadow-none"
          }`}
        >
          {isUploading ? "Uploading & Initializing..." : "Start Binary Diff Analysis"}
        </button>
      </div>
    </div>
  );
};
