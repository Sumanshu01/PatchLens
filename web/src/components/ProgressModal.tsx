import React, { useEffect, useState } from "react";
import { Loader2, CheckCircle2, AlertOctagon, Terminal } from "lucide-react";
import { subscribeToJobProgress, getJobStatus } from "../api";

interface ProgressModalProps {
  jobId: string;
  onCompleted: (resultId: number) => void;
  onError: (msg: string) => void;
}

const STAGE_TITLES: Record<string, string> = {
  queued: "Waiting in Queue...",
  loading_elf: "1. Parsing ELF Headers & Symbol Tables",
  disassembling: "2. Recursive Descent Disassembly (Capstone)",
  cfg_recovery: "3. Basic Block Splitting & CFG Recovery",
  fingerprinting: "4. Graph Kernels & Topological Fingerprints",
  function_matching: "5. Multi-Pass Function Matching Ladder",
  diffing_and_detecting: "6. Block-Level Diffing & Security Pattern Detectors",
  completed: "7. Analysis Finalized",
  failed: "Analysis Failed",
};

export const ProgressModal: React.FC<ProgressModalProps> = ({
  jobId,
  onCompleted,
  onError,
}) => {
  const [stage, setStage] = useState<string>("queued");
  const [progress, setProgress] = useState<number>(0);
  const [details, setDetails] = useState<string>("Initializing worker process...");
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    let checkInterval: any = null;

    const unsubscribe = subscribeToJobProgress(
      jobId,
      (event) => {
        setStage(event.stage);
        setProgress(event.progress);
        if (event.details) {
          setDetails(event.details);
          setLogs((prev) => [...prev.slice(-4), event.details]);
        }
        if (event.status === "completed" || event.progress === 100) {
          getJobStatus(jobId).then((st) => {
            if (st.result_id) onCompleted(st.result_id);
          });
        }
      },
      (err) => {
        console.warn("SSE connection error, falling back to polling:", err);
      }
    );

    // Fallback polling in case SSE is interrupted
    checkInterval = setInterval(async () => {
      try {
        const st = await getJobStatus(jobId);
        setStage(st.current_stage);
        setProgress(st.progress);
        if (st.stage_details) setDetails(st.stage_details);

        if (st.status === "completed" && st.result_id) {
          clearInterval(checkInterval);
          onCompleted(st.result_id);
        } else if (st.status === "failed") {
          clearInterval(checkInterval);
          onError(st.error_message || "Analysis failed");
        }
      } catch (e: any) {
        console.error("Polling error:", e);
      }
    }, 1500);

    return () => {
      unsubscribe();
      if (checkInterval) clearInterval(checkInterval);
    };
  }, [jobId, onCompleted, onError]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg rounded-2xl bg-[#efece6] border-2 border-slate-900 shadow-[6px_6px_0px_#141414] p-6 sm:p-8">
        {/* 4 Corner Brackets */}
        <span className="absolute -top-1.5 -left-1.5 w-3 h-3 border-t-2 border-l-2 border-slate-900" />
        <span className="absolute -top-1.5 -right-1.5 w-3 h-3 border-t-2 border-r-2 border-slate-900" />
        <span className="absolute -bottom-1.5 -left-1.5 w-3 h-3 border-b-2 border-l-2 border-slate-900" />
        <span className="absolute -bottom-1.5 -right-1.5 w-3 h-3 border-b-2 border-r-2 border-slate-900" />

        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-white border border-slate-900 flex items-center justify-center shadow-[2px_2px_0px_#141414]">
            {stage === "failed" ? (
              <AlertOctagon className="w-5 h-5 text-rose-600" />
            ) : progress === 100 ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            ) : (
              <Loader2 className="w-5 h-5 animate-spin text-indigo-700" />
            )}
          </div>
          <div>
            <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-indigo-700">
              // PIPELINE EXECUTION IN PROGRESS
            </div>
            <h3 className="font-black text-lg text-slate-900">
              {stage === "failed" ? "Analysis Encountered an Error" : "Diffing & Patch Analysis"}
            </h3>
            <p className="text-xs text-slate-600 font-mono mt-0.5">
              Job ID: <code className="font-bold text-slate-900 bg-white px-1.5 py-0.5 rounded border border-stone-300">{jobId}</code>
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-xs font-mono font-bold text-slate-800 mb-2">
            <span>{STAGE_TITLES[stage] || stage}</span>
            <span className="tabular-nums text-indigo-700">{progress}%</span>
          </div>
          <div className="w-full h-3.5 rounded-full bg-white border border-slate-900 p-0.5 overflow-hidden shadow-[1px_1px_0px_#141414]">
            <div
              className="h-full bg-gradient-to-r from-[#ffb347] via-[#ff5a5f] to-[#ff3d8b] transition-all duration-300 rounded-full"
              style={{ width: `${Math.max(5, progress)}%` }}
            />
          </div>
        </div>

        {/* Detail text */}
        <p className="text-xs text-slate-600 mb-6 font-mono italic">
          {details}
        </p>

        {/* Stage Log Snippet / Terminal Window */}
        <div className="rounded-xl bg-slate-950 text-emerald-400 p-4 font-mono text-[11px] space-y-1.5 border border-slate-800 shadow-[2px_2px_0px_#141414]">
          <div className="flex items-center space-x-2 text-slate-400 text-[10px] pb-2 border-b border-slate-800">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span className="font-bold uppercase tracking-wider">EXECUTION STAGES (LIVE STREAM)</span>
          </div>
          {logs.map((log, i) => (
            <div key={i} className="truncate">
              <span className="text-indigo-400 font-bold">&gt;</span> {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
