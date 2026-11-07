import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { GitCompare, Github, ArrowLeft, Linkedin } from "lucide-react";
import { Navbar } from "../components/Navbar";
import { UploadView } from "../components/UploadView";
import { ProgressModal } from "../components/ProgressModal";
import { DashboardView } from "../components/DashboardView";
import { FunctionDetailModal } from "../components/FunctionDetailModal";
import { CallGraphView } from "../components/CallGraphView";
import { AnalysisResult, RankedFunctionDiff } from "../types";
import { getAnalysisResult, getSampleCases } from "../api";

export const AnalyzerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const sampleParam = searchParams.get("sample");

  const [topBarDismissed, setTopBarDismissed] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [resultId, setResultId] = useState<number | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [selectedFnDiff, setSelectedFnDiff] = useState<RankedFunctionDiff | null>(null);
  const [showCallGraph, setShowCallGraph] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoadingSample, setIsLoadingSample] = useState(false);

  // Automatically load sample when `?sample=...` query param is present
  useEffect(() => {
    if (sampleParam && !resultId && !result && !activeJobId) {
      setIsLoadingSample(true);
      getSampleCases()
        .then((samples) => {
          const match = samples.find(
            (s) =>
              s.id === sampleParam ||
              s.cve.toLowerCase() === sampleParam.toLowerCase() ||
              s.id.toLowerCase().includes(sampleParam.toLowerCase())
          );
          if (match && match.result_id) {
            setResultId(match.result_id);
          } else {
            console.warn(`Sample "${sampleParam}" not ready or not found.`);
          }
        })
        .catch((err) => {
          console.error("Failed to load sample from URL:", err);
          setErrorMessage(`Failed to load sample: ${err.message}`);
        })
        .finally(() => {
          setIsLoadingSample(false);
        });
    }
  }, [sampleParam, resultId, result, activeJobId]);

  useEffect(() => {
    if (resultId) {
      getAnalysisResult(resultId)
        .then((res) => {
          setResult(res);
          setActiveJobId(null);
        })
        .catch((err) => {
          console.error("Failed loading result:", err);
          setErrorMessage(err.message);
        });
    }
  }, [resultId]);

  const handleNewAnalysis = () => {
    setActiveJobId(null);
    setResultId(null);
    setResult(null);
    setSelectedFnDiff(null);
    setShowCallGraph(false);
    setErrorMessage(null);
    if (sampleParam) {
      setSearchParams({});
    }
  };

  const handleSelectCallGraphNode = (addr: number) => {
    if (!result) return;
    const match = result.ranked_diffs.find(
      (d) => d.addr_b === addr || d.addr_a === addr
    );
    if (match) {
      setSelectedFnDiff(match);
    }
  };

  return (
    <div className="relative min-h-screen bg-[#efece6] text-slate-700 selection:bg-indigo-100 selection:text-indigo-900 font-sans overflow-x-hidden flex flex-col">
      {/* 3 Vertical Architectural Grid Guides (17%, 50%, 83%) matching Landing Page */}
      <div className="fixed top-0 bottom-0 left-[17%] w-px bg-stone-900/10 pointer-events-none z-10 hidden md:block" />
      <div className="fixed top-0 bottom-0 left-1/2 w-px bg-stone-900/10 pointer-events-none z-10 hidden md:block" />
      <div className="fixed top-0 bottom-0 left-[83%] w-px bg-stone-900/10 pointer-events-none z-10 hidden md:block" />

      {/* Top Announcement / Status Bar */}
      {!topBarDismissed && (
        <div className="w-full h-[36px] bg-[#efece6] border-b border-stone-900/10 font-mono text-xs text-slate-800 flex items-center justify-between px-4 sm:px-8 lg:px-12 z-50">
          <div className="flex items-center space-x-2 truncate">
            <span className="font-bold text-indigo-700 uppercase">Engine Status:</span>
            <span className="truncate">
              PatchLens Security Engine v0.1.0 — Ready for Binary Disassembly & CFG Analysis ↗
            </span>
          </div>
          <button
            onClick={() => setTopBarDismissed(true)}
            className="text-stone-500 hover:text-stone-900 font-mono text-base leading-none pl-4 transition-colors cursor-pointer"
            title="Dismiss announcement"
          >
            ×
          </button>
        </div>
      )}

      {/* Sticky Glass Navbar */}
      <Navbar onNewAnalysis={handleNewAnalysis} hasResult={!!result} />

      <main className="flex-1 relative z-20">
        {errorMessage && (
          <div className="max-w-4xl mx-auto my-6 p-4 rounded-xl bg-rose-50 border border-slate-900 text-rose-900 text-xs font-mono flex justify-between items-center shadow-[3px_3px_0px_#141414] relative">
            <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
            <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
            <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
            <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />
            <div className="flex items-center space-x-2">
              <span className="font-bold text-rose-700">[ERROR]</span>
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="font-bold px-2 py-0.5 text-rose-700 hover:text-rose-950 font-mono text-sm cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {isLoadingSample && (
          <div className="max-w-md mx-auto my-20 p-8 rounded-2xl bg-white/95 border border-slate-900 text-center shadow-[4px_4px_0px_#141414] relative">
            <span className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-slate-900" />
            <span className="absolute -top-1 -right-1 w-2 h-2 border-t border-r border-slate-900" />
            <span className="absolute -bottom-1 -left-1 w-2 h-2 border-b border-l border-slate-900" />
            <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-slate-900" />

            <div className="w-9 h-9 mx-auto mb-4 border-2 border-slate-900 border-t-indigo-700 rounded-full animate-spin" />
            <p className="text-sm font-bold text-slate-900 font-mono">
              Loading sample analysis ({sampleParam})...
            </p>
            <p className="text-xs text-slate-600 font-mono mt-1">
              Retrieving cached graph invariants and CFG blocks
            </p>
          </div>
        )}

        {/* 1. Upload View */}
        {!result && !activeJobId && !isLoadingSample && (
          <UploadView
            onAnalysisStarted={(jobId) => setActiveJobId(jobId)}
            onSampleSelected={(resId) => setResultId(resId)}
          />
        )}

        {/* 2. Progress Modal */}
        {activeJobId && (
          <ProgressModal
            jobId={activeJobId}
            onCompleted={(resId) => setResultId(resId)}
            onError={(msg) => {
              setErrorMessage(msg);
              setActiveJobId(null);
            }}
          />
        )}

        {/* 3. Dashboard / Results View */}
        {result && !showCallGraph && (
          <DashboardView
            result={result}
            onSelectFunction={(diff) => setSelectedFnDiff(diff)}
            onToggleCallGraph={() => setShowCallGraph(true)}
            showCallGraph={showCallGraph}
          />
        )}

        {/* 4. Match Explorer Call Graph View */}
        {result && showCallGraph && (
          <div>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
              <button
                onClick={() => setShowCallGraph(false)}
                className="group relative inline-flex items-center space-x-2 px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-slate-900 border border-slate-900 bg-white hover:bg-stone-50 shadow-[2px_2px_0px_#141414] hover:shadow-[3px_3px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all cursor-pointer"
              >
                <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
                <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
                <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
                <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />
                <ArrowLeft className="w-3.5 h-3.5 text-indigo-700 group-hover:-translate-x-0.5 transition-transform" />
                <span>Back to Functions Dashboard</span>
              </button>
            </div>
            <CallGraphView
              callgraph={result.callgraph}
              onSelectNode={handleSelectCallGraphNode}
            />
          </div>
        )}

        {/* 5. Function Detail Modal */}
        {selectedFnDiff && result && (
          <FunctionDetailModal
            resultId={result.id}
            fnDiff={selectedFnDiff}
            onClose={() => setSelectedFnDiff(null)}
          />
        )}
      </main>

      {/* Footer matching Landing Page style */}
      <footer className="py-8 bg-white border-t border-stone-900/10 text-xs text-slate-500 relative z-20 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex flex-col sm:flex-row items-center space-y-2 sm:space-y-0 sm:space-x-3 text-center sm:text-left">
            <div className="flex items-center space-x-2">
              <GitCompare className="w-4 h-4 text-indigo-600" />
              <span className="font-bold text-slate-800 font-mono">PatchLens</span>
              <span>— Automated Binary Diffing & Security Patch Localization · 2026</span>
            </div>
            <span className="hidden sm:inline text-slate-300">|</span>
            {/* Developer Tag */}
            <div className="inline-flex items-center space-x-2 bg-slate-50 border border-slate-200/80 px-2.5 py-1 rounded-full text-slate-600 font-mono text-[11px]">
              <span className="text-slate-500">Dev:</span>
              <span className="font-semibold text-slate-800">Sumanshu Jindal</span>
              <a
                href="https://github.com/Sumanshu01"
                target="_blank"
                rel="noreferrer"
                title="GitHub: Sumanshu01"
                className="text-slate-500 hover:text-slate-900 transition-colors inline-flex items-center"
              >
                <Github className="w-3.5 h-3.5" />
              </a>
              <a
                href="https://www.linkedin.com/in/sumanshu-jindal01/"
                target="_blank"
                rel="noreferrer"
                title="LinkedIn: sumanshu-jindal01"
                className="text-indigo-600 hover:text-indigo-800 transition-colors inline-flex items-center"
              >
                <Linkedin className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          <div className="flex items-center space-x-6 text-slate-600 font-mono text-[11px]">
            <Link to="/" className="hover:text-indigo-600 transition-colors">
              Home
            </Link>
            <button
              onClick={handleNewAnalysis}
              className="hover:text-indigo-600 transition-colors cursor-pointer"
            >
              New Analysis
            </button>
            <a
              href="https://github.com/Sumanshu01/PatchLens"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center space-x-1.5 hover:text-slate-900 transition-colors"
            >
              <Github className="w-3.5 h-3.5" />
              <span>GitHub</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};
