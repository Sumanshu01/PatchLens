import React, { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";
import {
  X,
  Layers,
  FileDiff,
  HelpCircle,
  ShieldAlert,
  Maximize2,
  Lock,
  Unlock,
} from "lucide-react";
import { CFGBlock, FunctionDetail, RankedFunctionDiff } from "../types";
import { getFunctionDetail } from "../api";

cytoscape.use(dagre);

interface FunctionDetailModalProps {
  resultId: number;
  fnDiff: RankedFunctionDiff;
  onClose: () => void;
}

export const FunctionDetailModal: React.FC<FunctionDetailModalProps> = ({
  resultId,
  fnDiff,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<"cfg" | "diff" | "match">("cfg");
  const [detail, setDetail] = useState<FunctionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedBlock, setSelectedBlock] = useState<{
    side: "A" | "B";
    block: CFGBlock;
  } | null>(null);
  const [syncPanZoom, setSyncPanZoom] = useState(true);

  const containerARef = useRef<HTMLDivElement>(null);
  const containerBRef = useRef<HTMLDivElement>(null);
  const cyAInstance = useRef<cytoscape.Core | null>(null);
  const cyBInstance = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    setLoading(true);
    getFunctionDetail(resultId, fnDiff.rank)
      .then((data) => {
        setDetail(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed loading function detail:", err);
        setLoading(false);
      });
  }, [resultId, fnDiff.rank]);

  // Cytoscape initialization for Side-by-side CFG in Light Mode
  useEffect(() => {
    if (activeTab !== "cfg" || !detail) return;

    // Accessible high-contrast node styling for light background
    const getNodeStyle = (type: string) => {
      switch (type) {
        case "added":
          return { bg: "#DCFCE7", border: "#16A34A", text: "#14532D" };
        case "removed":
          return { bg: "#FFE4E6", border: "#E11D48", text: "#881337" };
        case "modified":
          return { bg: "#FEF3C7", border: "#D97706", text: "#78350F" };
        default:
          return { bg: "#FFFFFF", border: "#CBD5E1", text: "#1E293B" };
      }
    };

    const getEdgeColor = (type: string) => {
      switch (type) {
        case "conditional_true":
          return "#16A34A";
        case "conditional_false":
          return "#DC2626";
        case "jump":
          return "#4338CA";
        case "call":
          return "#9333EA";
        default:
          return "#94A3B8";
      }
    };

    // Init Left Graph (CFG A - Baseline)
    if (containerARef.current && detail.cfg_a) {
      if (cyAInstance.current) cyAInstance.current.destroy();

      const elementsA: cytoscape.ElementDefinition[] = [];
      detail.cfg_a.blocks.forEach((bb) => {
        const badge =
          bb.change_type === "removed"
            ? "[-] "
            : bb.change_type === "modified"
            ? "[~] "
            : "[=] ";
        const style = getNodeStyle(bb.change_type);
        elementsA.push({
          data: {
            id: `bb_${bb.addr}`,
            label: `${badge}0x${bb.addr.toString(16)}\n(${bb.instructions.length} insns)`,
            bgColor: style.bg,
            borderColor: style.border,
            textColor: style.text,
            rawBlock: bb,
          },
        });
      });

      detail.cfg_a.edges.forEach((e, idx) => {
        elementsA.push({
          data: {
            id: `edge_a_${idx}`,
            source: `bb_${e.src}`,
            target: `bb_${e.dst}`,
            color: getEdgeColor(e.edge_type),
          },
        });
      });

      cyAInstance.current = cytoscape({
        container: containerARef.current,
        elements: elementsA,
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "text-wrap": "wrap",
              "text-valign": "center",
              "text-halign": "center",
              "font-size": "10px",
              "font-family": "JetBrains Mono, monospace",
              "font-weight": "bold",
              color: "data(textColor)",
              "background-color": "data(bgColor)",
              shape: "round-rectangle",
              width: "125px",
              height: "48px",
              "border-width": 2,
              "border-color": "data(borderColor)",
            },
          },
          {
            selector: "edge",
            style: {
              width: 2,
              "line-color": "data(color)",
              "target-arrow-color": "data(color)",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
            },
          },
        ],
        layout: {
          name: "dagre",
          rankDir: "TB",
          nodeSep: 35,
          rankSep: 45,
        } as any,
      });

      cyAInstance.current.on("tap", "node", (evt) => {
        const block = evt.target.data("rawBlock");
        setSelectedBlock({ side: "A", block });
      });
    }

    // Init Right Graph (CFG B - Patched)
    if (containerBRef.current && detail.cfg_b) {
      if (cyBInstance.current) cyBInstance.current.destroy();

      const elementsB: cytoscape.ElementDefinition[] = [];
      detail.cfg_b.blocks.forEach((bb) => {
        const badge =
          bb.change_type === "added"
            ? "[+] "
            : bb.change_type === "modified"
            ? "[~] "
            : "[=] ";
        const style = getNodeStyle(bb.change_type);
        elementsB.push({
          data: {
            id: `bb_${bb.addr}`,
            label: `${badge}0x${bb.addr.toString(16)}\n(${bb.instructions.length} insns)`,
            bgColor: style.bg,
            borderColor: style.border,
            textColor: style.text,
            rawBlock: bb,
          },
        });
      });

      detail.cfg_b.edges.forEach((e, idx) => {
        elementsB.push({
          data: {
            id: `edge_b_${idx}`,
            source: `bb_${e.src}`,
            target: `bb_${e.dst}`,
            color: getEdgeColor(e.edge_type),
          },
        });
      });

      cyBInstance.current = cytoscape({
        container: containerBRef.current,
        elements: elementsB,
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "text-wrap": "wrap",
              "text-valign": "center",
              "text-halign": "center",
              "font-size": "10px",
              "font-family": "JetBrains Mono, monospace",
              "font-weight": "bold",
              color: "data(textColor)",
              "background-color": "data(bgColor)",
              shape: "round-rectangle",
              width: "125px",
              height: "48px",
              "border-width": 2,
              "border-color": "data(borderColor)",
            },
          },
          {
            selector: "edge",
            style: {
              width: 2,
              "line-color": "data(color)",
              "target-arrow-color": "data(color)",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
            },
          },
        ],
        layout: {
          name: "dagre",
          rankDir: "TB",
          nodeSep: 35,
          rankSep: 45,
        } as any,
      });

      cyBInstance.current.on("tap", "node", (evt) => {
        const block = evt.target.data("rawBlock");
        setSelectedBlock({ side: "B", block });
      });
    }

    // Synchronize Pan/Zoom between CyA and CyB
    const cyA = cyAInstance.current;
    const cyB = cyBInstance.current;
    if (cyA && cyB && syncPanZoom) {
      let isSyncingA = false;
      let isSyncingB = false;

      cyA.on("pan zoom", () => {
        if (!isSyncingA && syncPanZoom) {
          isSyncingB = true;
          cyB.viewport({
            zoom: cyA.zoom(),
            pan: cyA.pan(),
          });
          isSyncingB = false;
        }
      });

      cyB.on("pan zoom", () => {
        if (!isSyncingB && syncPanZoom) {
          isSyncingA = true;
          cyA.viewport({
            zoom: cyB.zoom(),
            pan: cyB.pan(),
          });
          isSyncingA = false;
        }
      });
    }

    return () => {
      if (cyAInstance.current) cyAInstance.current.destroy();
      if (cyBInstance.current) cyBInstance.current.destroy();
    };
  }, [activeTab, detail, syncPanZoom]);

  const resetViews = () => {
    cyAInstance.current?.fit();
    cyBInstance.current?.fit();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-2 sm:p-4">
      <div className="w-full max-w-6xl h-[92vh] flex flex-col rounded-2xl bg-white shadow-2xl border border-stone-200 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between bg-stone-50/70">
          <div className="flex items-center space-x-3">
            {fnDiff.rank > 0 && (
              <span className="px-2.5 py-1 rounded-lg text-xs font-black bg-rose-600 text-white shadow-2xs">
                RANK #{fnDiff.rank}
              </span>
            )}
            <div>
              <h3 className="font-mono font-bold text-base text-slate-900 flex items-center space-x-2">
                <span>{fnDiff.name_a}</span>
                <span className="text-slate-400 font-normal">→</span>
                <span>{fnDiff.name_b}</span>
              </h3>
              <div className="flex items-center space-x-3 text-xs text-slate-500 mt-0.5">
                <span>
                  Similarity: <b className="text-slate-800">{(fnDiff.similarity * 100).toFixed(1)}%</b>
                </span>
                <span>•</span>
                <span>
                  Patch Score: <b className="text-slate-800">{fnDiff.patch_score.toFixed(4)}</b>
                </span>
                <span>•</span>
                <span className="capitalize font-medium text-slate-700">{fnDiff.classification}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-stone-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 border-b border-stone-200 flex items-center justify-between bg-white">
          <div className="flex space-x-6 text-xs font-semibold">
            <button
              onClick={() => setActiveTab("cfg")}
              className={`py-3.5 border-b-2 flex items-center space-x-2 transition-colors cursor-pointer ${
                activeTab === "cfg"
                  ? "border-indigo-600 text-indigo-700 font-bold"
                  : "border-transparent text-slate-500 hover:text-slate-900"
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Side-by-Side CFG</span>
            </button>

            <button
              onClick={() => setActiveTab("diff")}
              className={`py-3.5 border-b-2 flex items-center space-x-2 transition-colors cursor-pointer ${
                activeTab === "diff"
                  ? "border-indigo-600 text-indigo-700 font-bold"
                  : "border-transparent text-slate-500 hover:text-slate-900"
              }`}
            >
              <FileDiff className="w-4 h-4" />
              <span>Instruction-Level Diff</span>
            </button>

            <button
              onClick={() => setActiveTab("match")}
              className={`py-3.5 border-b-2 flex items-center space-x-2 transition-colors cursor-pointer ${
                activeTab === "match"
                  ? "border-indigo-600 text-indigo-700 font-bold"
                  : "border-transparent text-slate-500 hover:text-slate-900"
              }`}
            >
              <HelpCircle className="w-4 h-4" />
              <span>Why This Match?</span>
            </button>
          </div>

          {activeTab === "cfg" && (
            <div className="flex items-center space-x-2 text-xs">
              <button
                onClick={() => setSyncPanZoom(!syncPanZoom)}
                className={`px-2.5 py-1 rounded-lg border flex items-center space-x-1.5 font-medium transition-colors cursor-pointer ${
                  syncPanZoom
                    ? "bg-indigo-50 text-indigo-700 border-indigo-200"
                    : "bg-white text-slate-600 border-stone-300"
                }`}
              >
                {syncPanZoom ? <Lock className="w-3.5 h-3.5 text-indigo-600" /> : <Unlock className="w-3.5 h-3.5" />}
                <span>{syncPanZoom ? "Sync Zoom/Pan On" : "Sync Zoom/Pan Off"}</span>
              </button>

              <button
                onClick={resetViews}
                className="px-2.5 py-1 rounded-lg border border-stone-300 text-slate-600 hover:bg-stone-50 flex items-center space-x-1 cursor-pointer"
              >
                <Maximize2 className="w-3.5 h-3.5" />
                <span>Reset View</span>
              </button>
            </div>
          )}
        </div>

        {/* Tab Body */}
        <div className="flex-1 relative overflow-hidden bg-[#FAFAF9]">
          {loading ? (
            <div className="h-full flex items-center justify-center text-sm text-slate-400">
              Loading function diff details...
            </div>
          ) : (
            <>
              {/* TAB 1: CFG VIEWER */}
              {activeTab === "cfg" && (
                <div className="h-full grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-stone-200 relative">
                  {/* Left: CFG A */}
                  <div className="relative h-full flex flex-col bg-[#FAFAF9]">
                    <div className="p-3 bg-white/90 backdrop-blur-xs border-b border-stone-200 flex items-center justify-between text-xs font-semibold text-slate-700">
                      <span>Baseline CFG ({fnDiff.name_a})</span>
                      <span className="font-mono text-slate-400">
                        {detail?.cfg_a?.blocks.length || 0} blocks
                      </span>
                    </div>
                    <div ref={containerARef} className="flex-1 w-full h-full" />
                  </div>

                  {/* Right: CFG B */}
                  <div className="relative h-full flex flex-col bg-[#FAFAF9]">
                    <div className="p-3 bg-white/90 backdrop-blur-xs border-b border-stone-200 flex items-center justify-between text-xs font-semibold text-slate-700">
                      <span>Patched CFG ({fnDiff.name_b})</span>
                      <span className="font-mono text-slate-400">
                        {detail?.cfg_b?.blocks.length || 0} blocks
                      </span>
                    </div>
                    <div ref={containerBRef} className="flex-1 w-full h-full" />
                  </div>

                  {/* Block Inspector Drawer */}
                  {selectedBlock && (
                    <div className="absolute right-4 bottom-4 w-96 max-h-80 rounded-2xl bg-white text-slate-800 p-4 shadow-xl border border-stone-300 flex flex-col z-20">
                      <div className="flex items-center justify-between pb-2 border-b border-stone-200 mb-2">
                        <span className="font-mono font-bold text-xs text-slate-900">
                          Block 0x{selectedBlock.block.addr.toString(16)} (Side {selectedBlock.side})
                        </span>
                        <button
                          onClick={() => setSelectedBlock(null)}
                          className="text-slate-400 hover:text-slate-700"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="flex-1 overflow-auto font-mono text-[11px] space-y-1">
                        {selectedBlock.block.instructions.map((insn, i) => (
                          <div key={i} className="text-slate-700">
                            {insn}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: INSTRUCTION UNIFIED DIFF */}
              {activeTab === "diff" && (
                <div className="h-full overflow-auto p-6 bg-[#FAFAF9]">
                  {detail?.unified_diff ? (
                    <div className="max-w-4xl mx-auto rounded-2xl bg-white p-6 font-mono text-xs text-slate-800 border border-stone-200 shadow-card">
                      <pre className="whitespace-pre-wrap leading-relaxed">
                        {detail.unified_diff.split("\n").map((line, i) => {
                          let lineStyle = "text-slate-600";
                          if (line.startsWith("+") && !line.startsWith("+++")) {
                            lineStyle = "text-emerald-900 bg-emerald-50 px-1 py-0.5 rounded-xs border-l-2 border-emerald-500 font-semibold";
                          } else if (line.startsWith("-") && !line.startsWith("---")) {
                            lineStyle = "text-rose-900 bg-rose-50 px-1 py-0.5 rounded-xs border-l-2 border-rose-500 font-semibold";
                          } else if (line.startsWith("@@")) {
                            lineStyle = "text-indigo-700 font-bold py-1";
                          }
                          return (
                            <div key={i} className={lineStyle}>
                              {line}
                            </div>
                          );
                        })}
                      </pre>
                    </div>
                  ) : (
                    <div className="h-full flex items-center justify-center text-sm text-slate-500">
                      No instruction-level unified diff detected (functions identical or cosmetic).
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: WHY THIS MATCH? */}
              {activeTab === "match" && (
                <div className="max-w-4xl mx-auto p-6 space-y-6 overflow-auto h-full">
                  {/* Matching Engine Ladder Proof */}
                  <div className="p-6 rounded-2xl bg-white border border-stone-200 shadow-card">
                    <h4 className="text-sm font-bold text-slate-900 mb-2">
                      Multi-Pass Matching Attribution
                    </h4>
                    <p className="text-xs text-slate-500 mb-4">
                      This function pair was matched during:
                    </p>
                    <div className="p-4 rounded-xl bg-indigo-50/70 border border-indigo-200 flex items-center justify-between">
                      <div>
                        <span className="font-bold text-sm text-indigo-950 uppercase font-mono">
                          {fnDiff.matched_pass}
                        </span>
                        <p className="text-xs text-indigo-700 mt-0.5">
                          Assigned based on topological CFG and structural invariants
                        </p>
                      </div>
                      <div className="text-right font-mono font-bold text-indigo-700 text-lg">
                        {(fnDiff.confidence * 100).toFixed(0)}% Conf
                      </div>
                    </div>
                  </div>

                  {/* Fingerprint Similarity Breakdown */}
                  {detail?.fingerprint_breakdown && (
                    <div className="p-6 rounded-2xl bg-white border border-stone-200 shadow-card">
                      <h4 className="text-sm font-bold text-slate-900 mb-4">
                        Fingerprint Metric Invariants
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="p-4 rounded-xl bg-stone-50 border border-stone-200">
                          <span className="text-xs text-slate-500 font-medium">Mnemonic Cosine</span>
                          <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                            {((detail.fingerprint_breakdown.mnemonic_similarity || 0) * 100).toFixed(1)}%
                          </div>
                        </div>

                        <div className="p-4 rounded-xl bg-stone-50 border border-stone-200">
                          <span className="text-xs text-slate-500 font-medium">WL Subtree Kernel</span>
                          <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                            {((detail.fingerprint_breakdown.wl_graph_similarity || 0) * 100).toFixed(1)}%
                          </div>
                        </div>

                        <div className="p-4 rounded-xl bg-stone-50 border border-stone-200">
                          <span className="text-xs text-slate-500 font-medium">BinDiff MD-Index</span>
                          <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                            {((detail.fingerprint_breakdown.md_index_similarity || 0) * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Security Tags */}
                  {fnDiff.security_tags.length > 0 && (
                    <div className="p-6 rounded-2xl bg-white border border-stone-200 shadow-card">
                      <h4 className="text-sm font-bold text-slate-900 mb-3 flex items-center space-x-2">
                        <ShieldAlert className="w-4 h-4 text-rose-600" />
                        <span>Security Check Pattern Evidence ({fnDiff.security_tags.length})</span>
                      </h4>
                      <div className="space-y-3">
                        {fnDiff.security_tags.map((tag, i) => (
                          <div
                            key={i}
                            className="p-4 rounded-xl bg-rose-50/50 border border-rose-200 text-xs"
                          >
                            <div className="flex items-center justify-between font-bold text-rose-800 mb-1">
                              <span>{tag.tag_type}</span>
                              <span className="font-mono">{(tag.confidence * 100).toFixed(0)}% confidence</span>
                            </div>
                            <p className="text-slate-600 mb-2">
                              {tag.description}
                            </p>
                            <div className="font-mono text-[11px] p-2.5 rounded-lg bg-stone-900 text-stone-100 shadow-inner">
                              {tag.evidence}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
