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
          borderColor: n.is_changed ? "#E11D48" : "#CBD5E1",
          textColor: n.is_changed ? "#881337" : "#1E293B",
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
            width: "140px",
            height: "42px",
            "border-width": 2,
            "border-color": "data(borderColor)",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#94A3B8",
            "target-arrow-color": "#64748B",
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
      <div className="p-4 rounded-2xl bg-white border border-stone-200 shadow-card mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <span>Match Explorer — Call Graph Hierarchy</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Nodes in red represent changed and security-ranked functions. Click a node to view its diff details.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
            className="p-1.5 rounded-lg border border-stone-300 hover:bg-stone-50 text-slate-600 transition-colors cursor-pointer"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
            className="p-1.5 rounded-lg border border-stone-300 hover:bg-stone-50 text-slate-600 transition-colors cursor-pointer"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => cyRef.current?.fit()}
            className="p-1.5 rounded-lg border border-stone-300 hover:bg-stone-50 text-slate-600 transition-colors cursor-pointer"
            title="Fit View"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="w-full h-[650px] rounded-2xl bg-[#FAFAF9] border border-stone-200 overflow-hidden shadow-inner">
        <div ref={containerRef} className="w-full h-full" />
      </div>
    </div>
  );
};
