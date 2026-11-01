import React, { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";
import { ZoomIn, ZoomOut, Maximize2, ShieldAlert } from "lucide-react";
import { CallGraphData } from "../types";

cytoscape.use(dagre);

interface CallGraphViewProps {
  callgraph: CallGraphData;
  onSelectNode: (funcAddr: number) => void;
}

export const CallGraphView: React.FC<CallGraphViewProps> = ({
  callgraph,
  onSelectNode,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (cyRef.current) cyRef.current.destroy();

    const elements: cytoscape.ElementDefinition[] = [];

    callgraph.nodes.forEach((n) => {
      elements.push({
        data: {
          id: n.id,
          label: n.rank > 0 ? `#${n.rank} ${n.name}` : n.name,
          bgColor: n.is_changed ? "#FFE4E6" : "#FFFFFF",
          borderColor: n.is_changed ? "#E11D48" : "#141414",
          textColor: n.is_changed ? "#881337" : "#0F172A",
          rawAddr: n.addr,
          isChanged: n.is_changed,
        },
      });
    });

    callgraph.edges.forEach((e, idx) => {
      elements.push({
        data: {
          id: `cg_edge_${idx}`,
          source: e.source,
          target: e.target,
        },
      });
    });

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "10px",
            "font-family": "JetBrains Mono, monospace",
            "font-weight": "bold",
            color: "data(textColor)",
            "background-color": "data(bgColor)",
            shape: "round-rectangle",
            width: "148px",
            height: "44px",
            "border-width": 1.5,
            "border-color": "data(borderColor)",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#475569",
            "target-arrow-color": "#1E293B",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
      ],
      layout: {
        name: "dagre",
        rankDir: "LR",
        nodeSep: 40,
        rankSep: 60,
      } as any,
    });

    cyRef.current.on("tap", "node", (evt) => {
      const addr = evt.target.data("rawAddr");
      if (addr) onSelectNode(addr);
    });

    return () => {
      if (cyRef.current) cyRef.current.destroy();
    };
  }, [callgraph, onSelectNode]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header Card */}
      <div className="relative p-5 rounded-2xl bg-white/95 border border-slate-900/40 shadow-[3px_3px_0px_#141414] backdrop-blur-xs mb-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        {/* 4 Corner Brackets */}
        <span className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-slate-900" />
        <span className="absolute -top-1 -right-1 w-2 h-2 border-t border-r border-slate-900" />
        <span className="absolute -bottom-1 -left-1 w-2 h-2 border-b border-l border-slate-900" />
        <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-slate-900" />

        <div>
          <div className="font-mono text-xs font-bold uppercase tracking-wider text-indigo-700 mb-0.5">
            // TOPOLOGICAL EXPLORER
          </div>
          <h3 className="text-base font-black text-slate-900 flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <span>Match Explorer — Call Graph Hierarchy</span>
          </h3>
          <p className="text-xs text-slate-600 mt-1 font-mono">
            Nodes in red represent changed and security-ranked functions. Click a node to view its diff details.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
            className="p-2 rounded-lg border border-slate-900 bg-white hover:bg-stone-50 shadow-[1px_1px_0px_#141414] active:shadow-none text-slate-800 transition-all cursor-pointer"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
            className="p-2 rounded-lg border border-slate-900 bg-white hover:bg-stone-50 shadow-[1px_1px_0px_#141414] active:shadow-none text-slate-800 transition-all cursor-pointer"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => cyRef.current?.fit()}
            className="p-2 rounded-lg border border-slate-900 bg-white hover:bg-stone-50 shadow-[1px_1px_0px_#141414] active:shadow-none text-slate-800 transition-all cursor-pointer"
            title="Fit View"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Cytoscape Canvas Container */}
      <div className="relative w-full h-[650px] rounded-2xl bg-[#efece6]/60 border border-slate-900 shadow-[3px_3px_0px_#141414] overflow-hidden">
        {/* Subtle architectural grid lines */}
        <div className="absolute inset-0 bg-[radial-gradient(#141414_0.75px,transparent_0.75px)] [background-size:16px_16px] opacity-10 pointer-events-none" />
        <div ref={containerRef} className="w-full h-full relative z-10" />
      </div>
    </div>
  );
};
