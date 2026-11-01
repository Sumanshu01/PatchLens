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

  // Cytoscape initialization for Side-by-side CFG
  useEffect(() => {
    if (activeTab !== "cfg" || !detail) return;

    const getNodeStyle = (type: string) => {
      switch (type) {
        case "added":
          return { bg: "#DCFCE7", border: "#16A34A", text: "#14532D" };
        case "removed":
          return { bg: "#FFE4E6", border: "#E11D48", text: "#881337" };
        case "modified":
          return { bg: "#FEF3C7", border: "#D97706", text: "#78350F" };
        default:
          return { bg: "#FFFFFF", border: "#141414", text: "#0F172A" };
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
          return "#475569";
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
              width: "128px",
              height: "48px",
              "border-width": 1.5,
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
              width: "128px",
              height: "48px",
              "border-width": 1.5,
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-2 sm:p-4">
      <div className="relative w-full max-w-6xl h-[92vh] flex flex-col rounded-2xl bg-[#efece6] shadow-[8px_8px_0px_#141414] border-2 border-slate-900 overflow-hidden">
        {/* 4 Corner Brackets */}
        <span className="absolute -top-1.5 -left-1.5 w-3 h-3 border-t-2 border-l-2 border-slate-900 z-50 pointer-events-none" />
        <span className="absolute -top-1.5 -right-1.5 w-3 h-3 border-t-2 border-r-2 border-slate-900 z-50 pointer-events-none" />
        <span className="absolute -bottom-1.5 -left-1.5 w-3 h-3 border-b-2 border-l-2 border-slate-900 z-50 pointer-events-none" />
        <span className="absolute -bottom-1.5 -right-1.5 w-3 h-3 border-b-2 border-r-2 border-slate-900 z-50 pointer-events-none" />

        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-900 bg-white/95 flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            {fnDiff.rank > 0 && (
              <span className="px-3 py-1 rounded font-mono font-black text-xs bg-rose-600 text-white shadow-[1px_1px_0px_#141414]">
                RANK #{fnDiff.rank}
              </span>
            )}
            <div>
              <h3 className="font-mono font-bold text-base text-slate-900 flex items-center space-x-2">
                <span>{fnDiff.name_a}</span>
                <span className="text-slate-400 font-normal">→</span>
                <span>{fnDiff.name_b}</span>
              </h3>
              <div className="flex items-center space-x-3 text-xs font-mono text-slate-600 mt-0.5">
                <span>
                  Similarity: <b className="text-slate-950 font-bold">{(fnDiff.similarity * 100).toFixed(1)}%</b>
                </span>
                <span>•</span>
                <span>
                  Patch Score: <b className="text-slate-950 font-bold">{fnDiff.patch_score.toFixed(4)}</b>
                </span>
                <span>•</span>
                <span className="capitalize font-bold text-indigo-700">{fnDiff.classification}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="p-2 rounded-lg border border-slate-900 bg-white hover:bg-stone-50 shadow-[1px_1px_0px_#141414] active:shadow-none text-slate-800 transition-all cursor-pointer"
              title="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation (Neo-brutalist Tab Strip) */}
        <div className="px-6 py-2.5 border-b border-slate-900 bg-[#efece6] flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center space-x-2 font-mono text-xs uppercase tracking-wider">
            <button
              onClick={() => setActiveTab("cfg")}
              className={`relative inline-flex items-center space-x-2 px-3.5 py-2 border transition-all cursor-pointer font-bold ${
                activeTab === "cfg"
                  ? "bg-white text-slate-900 border-slate-900 shadow-[2px_2px_0px_#141414]"
                  : "bg-transparent text-slate-700 border-transparent hover:border-slate-900 hover:bg-white"
              }`}
            >
              {activeTab === "cfg" && (
                <>
                  <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
                  <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
                  <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
                  <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />
                </>
              )}
              <Layers className="w-3.5 h-3.5 text-indigo-700" />
              <span>[01] Side-by-Side CFG</span>
            </button>

            <button
              onClick={() => setActiveTab("diff")}
              className={`relative inline-flex items-center space-x-2 px-3.5 py-2 border transition-all cursor-pointer font-bold ${
                activeTab === "diff"
                  ? "bg-white text-slate-900 border-slate-900 shadow-[2px_2px_0px_#141414]"
                  : "bg-transparent text-slate-700 border-transparent hover:border-slate-900 hover:bg-white"
              }`}
            >
              {activeTab === "diff" && (
                <>
                  <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
                  <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
                  <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
                  <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />
                </>
              )}
              <FileDiff className="w-3.5 h-3.5 text-indigo-700" />
              <span>[02] Instruction-Level Diff</span>
            </button>

            <button
              onClick={() => setActiveTab("match")}
              className={`relative inline-flex items-center space-x-2 px-3.5 py-2 border transition-all cursor-pointer font-bold ${
                activeTab === "match"
                  ? "bg-white text-slate-900 border-slate-900 shadow-[2px_2px_0px_#141414]"
                  : "bg-transparent text-slate-700 border-transparent hover:border-slate-900 hover:bg-white"
              }`}
            >
              {activeTab === "match" && (
                <>
                  <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
                  <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
                  <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
                  <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />
                </>
              )}
              <HelpCircle className="w-3.5 h-3.5 text-indigo-700" />
              <span>[03] Why This Match?</span>
            </button>
          </div>

          {activeTab === "cfg" && (
            <div className="flex items-center space-x-2 font-mono text-xs">
              <button
                onClick={() => setSyncPanZoom(!syncPanZoom)}
                className={`px-3 py-1.5 rounded border border-slate-900 flex items-center space-x-1.5 font-bold shadow-[1px_1px_0px_#141414] active:shadow-none transition-all cursor-pointer ${
                  syncPanZoom ? "bg-white text-indigo-700" : "bg-stone-200 text-slate-700"
                }`}
              >
                {syncPanZoom ? <Lock className="w-3 h-3 text-indigo-700" /> : <Unlock className="w-3 h-3" />}
                <span>{syncPanZoom ? "Sync Zoom: ON" : "Sync Zoom: OFF"}</span>
              </button>

              <button
                onClick={resetViews}
                className="px-3 py-1.5 rounded border border-slate-900 bg-white hover:bg-stone-50 shadow-[1px_1px_0px_#141414] active:shadow-none text-slate-800 flex items-center space-x-1 font-bold cursor-pointer"
              >
                <Maximize2 className="w-3 h-3" />
                <span>Reset View</span>
              </button>
            </div>
          )}
        </div>

        {/* Tab Body */}
        <div className="flex-1 relative overflow-hidden bg-[#efece6]/60">
          {loading ? (
            <div className="h-full flex items-center justify-center font-mono text-xs text-slate-500">
              // Loading function diff details and basic blocks...
            </div>
          ) : (
            <>
              {/* TAB 1: CFG VIEWER */}
              {activeTab === "cfg" && (
                <div className="h-full grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-900 relative">
                  {/* Left: CFG A */}
                  <div className="relative h-full flex flex-col bg-[#efece6]/50">
                    <div className="p-3 bg-white/95 border-b border-slate-900 flex items-center justify-between text-xs font-mono font-bold text-slate-800">
                      <span>BASELINE CFG ({fnDiff.name_a})</span>
                      <span className="text-slate-500">
                        {detail?.cfg_a?.blocks.length || 0} blocks
                      </span>
                    </div>
                    <div ref={containerARef} className="flex-1 w-full h-full" />
                  </div>

                  {/* Right: CFG B */}
                  <div className="relative h-full flex flex-col bg-[#efece6]/50">
                    <div className="p-3 bg-white/95 border-b border-slate-900 flex items-center justify-between text-xs font-mono font-bold text-slate-800">
                      <span>PATCHED CFG ({fnDiff.name_b})</span>
                      <span className="text-slate-500">
                        {detail?.cfg_b?.blocks.length || 0} blocks
                      </span>
                    </div>
                    <div ref={containerBRef} className="flex-1 w-full h-full" />
                  </div>

                  {/* Block Inspector Drawer */}
                  {selectedBlock && (
                    <div className="absolute right-4 bottom-4 w-96 max-h-80 rounded-2xl bg-white text-slate-800 p-4 shadow-[4px_4px_0px_#141414] border-2 border-slate-900 flex flex-col z-20">
                      <div className="flex items-center justify-between pb-2 border-b border-stone-200 mb-2">
                        <span className="font-mono font-bold text-xs text-slate-900">
                          Block 0x{selectedBlock.block.addr.toString(16)} (Side {selectedBlock.side})
                        </span>
                        <button
                          onClick={() => setSelectedBlock(null)}
                          className="text-slate-500 hover:text-slate-900"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="flex-1 overflow-auto font-mono text-[11px] space-y-1">
                        {selectedBlock.block.instructions.map((insn, i) => (
                          <div key={i} className="text-slate-800">
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
                <div className="h-full overflow-auto p-6 bg-[#efece6]/60">
                  {detail?.unified_diff ? (
                    <div className="max-w-4xl mx-auto rounded-2xl bg-slate-950 p-6 font-mono text-xs text-slate-200 border-2 border-slate-900 shadow-[4px_4px_0px_#141414]">
                      <div className="pb-3 mb-4 border-b border-slate-800 flex items-center justify-between text-slate-400 text-[11px]">
                        <span>UNIFIED DISASSEMBLY DIFF</span>
                        <span className="text-indigo-400">NORMALIZED REGISTERS</span>
                      </div>
                      <pre className="whitespace-pre-wrap leading-relaxed font-mono">
                        {detail.unified_diff.split("\n").map((line, i) => {
                          let lineStyle = "text-slate-400";
                          if (line.startsWith("+") && !line.startsWith("+++")) {
                            lineStyle = "text-emerald-300 bg-emerald-950/70 px-1 py-0.5 border-l-2 border-emerald-400 font-semibold";
                          } else if (line.startsWith("-") && !line.startsWith("---")) {
                            lineStyle = "text-rose-300 bg-rose-950/70 px-1 py-0.5 border-l-2 border-rose-400 font-semibold";
                          } else if (line.startsWith("@@")) {
                            lineStyle = "text-indigo-400 font-bold py-1";
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
                    <div className="h-full flex items-center justify-center font-mono text-xs text-slate-500">
                      // No instruction-level unified diff detected (functions identical or cosmetic).
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: WHY THIS MATCH? */}
              {activeTab === "match" && (
                <div className="max-w-4xl mx-auto p-6 space-y-6 overflow-auto h-full">
                  {/* Matching Engine Ladder Proof */}
                  <div className="p-6 rounded-2xl bg-white border border-slate-900 shadow-[3px_3px_0px_#141414] relative">
                    <span className="font-mono text-xs font-bold uppercase tracking-wider text-indigo-700 block mb-1">
                      // PASS CLASSIFICATION
                    </span>
                    <h4 className="text-base font-black text-slate-900 mb-1">
                      Multi-Pass Matching Attribution
                    </h4>
                    <p className="text-xs text-slate-600 mb-4 font-mono">
                      This function pair was matched during the matching cascade:
                    </p>
                    <div className="p-4 rounded-xl bg-[#efece6] border border-slate-900 flex items-center justify-between">
                      <div>
                        <span className="font-black text-sm text-slate-950 uppercase font-mono">
                          {fnDiff.matched_pass}
                        </span>
                        <p className="text-xs text-slate-600 mt-0.5 font-mono">
                          Assigned based on topological CFG and structural invariants
                        </p>
                      </div>
                      <div className="text-right font-mono font-black text-indigo-700 text-lg">
                        {(fnDiff.confidence * 100).toFixed(0)}% Conf
                      </div>
                    </div>
                  </div>

                  {/* Fingerprint Similarity Breakdown */}
                  {detail?.fingerprint_breakdown && (
                    <div className="p-6 rounded-2xl bg-white border border-slate-900 shadow-[3px_3px_0px_#141414]">
                      <span className="font-mono text-xs font-bold uppercase tracking-wider text-indigo-700 block mb-1">
                        // STRUCTURAL INVARIANTS
                      </span>
                      <h4 className="text-base font-black text-slate-900 mb-4">
                        Fingerprint Metric Invariants
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="p-4 rounded-xl bg-[#efece6] border border-slate-900">
                          <span className="text-xs font-mono font-bold text-slate-600 uppercase">Mnemonic Cosine</span>
                          <div className="text-xl font-black font-mono text-slate-900 mt-1">
                            {((detail.fingerprint_breakdown.mnemonic_similarity || 0) * 100).toFixed(1)}%
                          </div>
                        </div>

                        <div className="p-4 rounded-xl bg-[#efece6] border border-slate-900">
                          <span className="text-xs font-mono font-bold text-slate-600 uppercase">WL Subtree Kernel</span>
                          <div className="text-xl font-black font-mono text-indigo-700 mt-1">
                            {((detail.fingerprint_breakdown.wl_graph_similarity || 0) * 100).toFixed(1)}%
                          </div>
                        </div>

                        <div className="p-4 rounded-xl bg-[#efece6] border border-slate-900">
                          <span className="text-xs font-mono font-bold text-slate-600 uppercase">BinDiff MD-Index</span>
                          <div className="text-xl font-black font-mono text-slate-900 mt-1">
                            {((detail.fingerprint_breakdown.md_index_similarity || 0) * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Security Tags */}
                  {fnDiff.security_tags.length > 0 && (
                    <div className="p-6 rounded-2xl bg-white border border-slate-900 shadow-[3px_3px_0px_#141414]">
                      <span className="font-mono text-xs font-bold uppercase tracking-wider text-rose-700 block mb-1">
                        // HEURISTIC EVIDENCE
                      </span>
                      <h4 className="text-base font-black text-slate-900 mb-3 flex items-center space-x-2">
                        <ShieldAlert className="w-4 h-4 text-rose-600" />
                        <span>Security Check Pattern Evidence ({fnDiff.security_tags.length})</span>
                      </h4>
                      <div className="space-y-3">
                        {fnDiff.security_tags.map((tag, i) => (
                          <div
                            key={i}
                            className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-xs shadow-2xs"
                          >
                            <div className="flex items-center justify-between font-bold text-rose-900 mb-1 font-mono">
                              <span>{tag.tag_type}</span>
                              <span>{(tag.confidence * 100).toFixed(0)}% confidence</span>
                            </div>
                            <p className="text-slate-700 mb-2 font-mono">
                              {tag.description}
                            </p>
                            <div className="font-mono text-[11px] p-2.5 rounded-lg bg-slate-900 text-emerald-400 shadow-inner">
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
