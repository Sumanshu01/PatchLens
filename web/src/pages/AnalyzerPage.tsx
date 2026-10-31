import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
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
    <div className="min-h-screen flex flex-col bg-[#FAFAF9] text-slate-600">
      <Navbar onNewAnalysis={handleNewAnalysis} hasResult={!!result} />

      <main className="flex-1">
        {errorMessage && (
          <div className="max-w-4xl mx-auto my-4 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex justify-between items-center shadow-xs">
            <span>{errorMessage}</span>
            <button
              onClick={() => setErrorMessage(null)}
              className="font-bold px-2 py-0.5 text-rose-600 hover:text-rose-900"
            >
              ✕
            </button>
          </div>
        )}

        {isLoadingSample && (
          <div className="max-w-md mx-auto my-16 p-8 rounded-2xl bg-white border border-stone-200 text-center shadow-sm">
            <div className="w-8 h-8 mx-auto mb-3 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm font-semibold text-slate-800">
              Loading sample analysis ({sampleParam})...
            </p>
            <p className="text-xs text-slate-500 mt-1">Retrieving cached graph invariants and CFGs</p>
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
                className="text-xs font-semibold text-indigo-700 hover:text-indigo-800 hover:underline inline-flex items-center space-x-1"
              >
                <span>← Back to Functions Dashboard</span>
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

      <footer className="py-6 border-t border-stone-200 bg-white text-center text-xs text-slate-500">
        PatchLens — Automated Binary Diffing & Security Patch Localization • Powered by Capstone & Weisfeiler-Lehman Graph Invariants
      </footer>
    </div>
  );
};
