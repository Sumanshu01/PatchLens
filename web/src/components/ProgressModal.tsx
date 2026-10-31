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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 sm:p-8 shadow-2xl border border-stone-200">
        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-700">
            {stage === "failed" ? (
              <AlertOctagon className="w-6 h-6 text-rose-600" />
            ) : progress === 100 ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-600" />
            ) : (
              <Loader2 className="w-6 h-6 animate-spin text-indigo-700" />
            )}
          </div>
          <div>
            <h3 className="font-bold text-lg text-slate-900">
              {stage === "failed" ? "Analysis Encountered an Error" : "Diffing & Patch Analysis in Progress"}
            </h3>
            <p className="text-xs text-slate-500">
              Job ID: <code className="font-mono text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded">{jobId}</code>
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-xs font-semibold text-slate-700 mb-2">
            <span>{STAGE_TITLES[stage] || stage}</span>
            <span className="tabular-nums font-mono text-indigo-700">{progress}%</span>
          </div>
          <div className="w-full h-3 rounded-full bg-stone-100 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-700 via-indigo-600 to-blue-600 transition-all duration-300 rounded-full"
              style={{ width: `${Math.max(5, progress)}%` }}
            />
          </div>
        </div>

        {/* Detail text */}
        <p className="text-xs text-slate-500 mb-6 italic">
          {details}
        </p>

        {/* Stage Log Snippet */}
        <div className="rounded-xl bg-stone-900 text-stone-200 p-3.5 font-mono text-[11px] space-y-1 shadow-inner">
          <div className="flex items-center space-x-1.5 text-stone-400 text-[10px] pb-1.5 border-b border-stone-800">
            <Terminal className="w-3 h-3 text-indigo-400" />
            <span>EXECUTION STAGES</span>
          </div>
          {logs.map((log, i) => (
            <div key={i} className="truncate">
              <span className="text-indigo-400">&gt;</span> {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
