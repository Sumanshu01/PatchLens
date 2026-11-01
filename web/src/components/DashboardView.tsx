import React, { useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  ShieldAlert,
  Search,
  Network,
  Download,
  ArrowRight,
} from "lucide-react";
import { AnalysisResult, RankedFunctionDiff } from "../types";
import { getExportJsonUrl, getExportMarkdownUrl } from "../api";

interface DashboardViewProps {
  result: AnalysisResult;
  onSelectFunction: (diff: RankedFunctionDiff) => void;
  onToggleCallGraph: () => void;
  showCallGraph: boolean;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  result,
  onSelectFunction,
  onToggleCallGraph,
  showCallGraph,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [classFilter, setClassFilter] = useState<string>("all");
  const [tagFilter, setTagFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"rank" | "score" | "sim">("score");

  const summary = result.summary;

  const filteredFunctions = useMemo(() => {
    return result.ranked_diffs
      .filter((fn) => {
        if (
          searchTerm &&
          !fn.name_a.toLowerCase().includes(searchTerm.toLowerCase()) &&
          !fn.name_b.toLowerCase().includes(searchTerm.toLowerCase()) &&
          !(fn.addr_a && fn.addr_a.toString(16).includes(searchTerm.toLowerCase())) &&
          !(fn.addr_b && fn.addr_b.toString(16).includes(searchTerm.toLowerCase()))
        ) {
          return false;
        }

        if (classFilter !== "all" && fn.classification !== classFilter) {
          return false;
        }

        if (tagFilter !== "all") {
          const hasTag = fn.security_tags.some((t) => t.tag_type === tagFilter);
          if (!hasTag) return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "rank") {
          if (a.rank === 0) return 1;
          if (b.rank === 0) return -1;
          return a.rank - b.rank;
        }
        if (sortBy === "sim") {
          return a.similarity - b.similarity;
        }
        return b.patch_score - a.patch_score;
      });
  }, [result.ranked_diffs, searchTerm, classFilter, tagFilter, sortBy]);

  // Virtualizer for table
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: filteredFunctions.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64,
    overscan: 10,
  });

  const getBadgeStyle = (classification: string) => {
    switch (classification) {
      case "changed-semantic":
        return "bg-amber-50 text-amber-950 border-amber-400";
      case "changed-cosmetic":
        return "bg-sky-50 text-sky-950 border-sky-400";
      case "added":
        return "bg-emerald-50 text-emerald-950 border-emerald-400";
      case "removed":
        return "bg-rose-50 text-rose-950 border-rose-400";
      default:
        return "bg-stone-100 text-slate-800 border-stone-300";
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Top Banner & Export Actions with Neo-brutalist styling */}
      <div className="relative p-6 sm:p-7 rounded-2xl bg-white/95 border border-slate-900/40 shadow-[3px_3px_0px_#141414] backdrop-blur-xs">
        {/* 4 Corner Brackets */}
        <span className="absolute -top-1 -left-1 w-2 h-2 border-t border-l border-slate-900" />
        <span className="absolute -top-1 -right-1 w-2 h-2 border-t border-r border-slate-900" />
        <span className="absolute -bottom-1 -left-1 w-2 h-2 border-b border-l border-slate-900" />
        <span className="absolute -bottom-1 -right-1 w-2 h-2 border-b border-r border-slate-900" />

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-5">
          <div>
            <div className="font-mono text-xs font-bold uppercase tracking-wider text-indigo-700 mb-1">
              // RUNTIME ANALYSIS REPORT
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                Diff Results & Security Localization
              </h2>
              <span className="text-[11px] px-2.5 py-0.5 rounded font-mono font-bold bg-[#efece6] text-slate-800 border border-slate-900 shadow-[1px_1px_0px_#141414]">
                Pair: {result.pair_hash.slice(0, 16)}...
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-600 mt-1 font-mono">
              Matched {summary.matched_count} functions across binaries with {summary.top_patch_candidates_count} suspicious security patch candidates.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={onToggleCallGraph}
              className={`group relative inline-flex items-center space-x-2 px-4 py-2.5 font-mono text-xs font-bold uppercase tracking-wider border border-slate-900 shadow-[2px_2px_0px_#141414] hover:shadow-[3px_3px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all cursor-pointer ${
                showCallGraph
                  ? "bg-slate-900 text-white"
                  : "bg-white hover:bg-stone-50 text-slate-900"
              }`}
            >
              <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
              <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />

              <Network className="w-3.5 h-3.5 text-indigo-600" />
              <span>{showCallGraph ? "View Functions Table" : "Match Explorer (Call Graph)"}</span>
            </button>

            <a
              href={getExportJsonUrl(result.id)}
              download
              className="group relative inline-flex items-center space-x-1.5 px-3.5 py-2.5 font-mono text-xs font-bold uppercase tracking-wider text-slate-900 border border-slate-900 bg-white hover:bg-stone-50 shadow-[2px_2px_0px_#141414] hover:shadow-[3px_3px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all"
            >
              <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
              <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />

              <Download className="w-3.5 h-3.5 text-indigo-700" />
              <span>JSON</span>
            </a>

            <a
              href={getExportMarkdownUrl(result.id)}
              download
              className="group relative inline-flex items-center space-x-1.5 px-3.5 py-2.5 font-mono text-xs font-bold uppercase tracking-wider text-slate-900 border border-slate-900 bg-white hover:bg-stone-50 shadow-[2px_2px_0px_#141414] hover:shadow-[3px_3px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all"
            >
              <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
              <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />

              <Download className="w-3.5 h-3.5 text-indigo-700" />
              <span>Markdown</span>
            </a>
          </div>
        </div>
      </div>

      {/* Summary Cards with Corner Brackets & Brutalist Shadows */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Total Baseline */}
        <div className="relative p-4 rounded-xl bg-white/95 border border-slate-900/30 shadow-[2px_2px_0px_#141414] hover:-translate-y-0.5 transition-transform">
          <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900" />
          <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900" />
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
            Total Baseline
          </span>
          <div className="text-2xl font-black text-slate-900 font-mono mt-1 tabular-nums">
            {summary.total_functions_a}
          </div>
          <span className="text-[10px] font-mono text-slate-500">Functions</span>
        </div>

        {/* Matched Pairs */}
        <div className="relative p-4 rounded-xl bg-white/95 border border-slate-900/30 shadow-[2px_2px_0px_#141414] hover:-translate-y-0.5 transition-transform">
          <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900" />
          <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900" />
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
            Matched Pairs
          </span>
          <div className="text-2xl font-black text-indigo-700 font-mono mt-1 tabular-nums">
            {summary.matched_count}
          </div>
          <span className="text-[10px] font-mono text-indigo-600 font-bold">
            {summary.total_functions_a > 0
              ? `${((summary.matched_count / summary.total_functions_a) * 100).toFixed(1)}% match`
              : "0%"}
          </span>
        </div>

        {/* Semantic Changes */}
        <div className="relative p-4 rounded-xl bg-white/95 border border-rose-500/40 shadow-[2px_2px_0px_#141414] hover:-translate-y-0.5 transition-transform">
          <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-rose-600" />
          <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-rose-600" />
          <span className="text-[10px] font-mono font-bold text-rose-700 uppercase tracking-wider block flex items-center space-x-1">
            <span>Semantic Changes</span>
            <ShieldAlert className="w-3 h-3 text-rose-600 inline" />
          </span>
          <div className="text-2xl font-black text-rose-700 font-mono mt-1 tabular-nums">
            {summary.changed_semantic_count}
          </div>
          <span className="text-[10px] font-mono text-rose-600 font-bold">Logic modified</span>
        </div>

        {/* Cosmetic Only */}
        <div className="relative p-4 rounded-xl bg-white/95 border border-slate-900/30 shadow-[2px_2px_0px_#141414] hover:-translate-y-0.5 transition-transform">
          <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900" />
          <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900" />
          <span className="text-[10px] font-mono font-bold text-amber-800 uppercase tracking-wider block">
            Cosmetic Only
          </span>
          <div className="text-2xl font-black text-amber-800 font-mono mt-1 tabular-nums">
            {summary.changed_cosmetic_count}
          </div>
          <span className="text-[10px] font-mono text-amber-700">Regs / layout noise</span>
        </div>

        {/* Added */}
        <div className="relative p-4 rounded-xl bg-white/95 border border-slate-900/30 shadow-[2px_2px_0px_#141414] hover:-translate-y-0.5 transition-transform">
          <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900" />
          <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900" />
          <span className="text-[10px] font-mono font-bold text-emerald-800 uppercase tracking-wider block">
            Added
          </span>
          <div className="text-2xl font-black text-emerald-800 font-mono mt-1 tabular-nums">
            {summary.unmatched_b_count}
          </div>
          <span className="text-[10px] font-mono text-emerald-700">New functions</span>
        </div>

        {/* Removed */}
        <div className="relative p-4 rounded-xl bg-white/95 border border-slate-900/30 shadow-[2px_2px_0px_#141414] hover:-translate-y-0.5 transition-transform">
          <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900" />
          <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900" />
          <span className="text-[10px] font-mono font-bold text-slate-700 uppercase tracking-wider block">
            Removed
          </span>
          <div className="text-2xl font-black text-slate-900 font-mono mt-1 tabular-nums">
            {summary.unmatched_a_count}
          </div>
          <span className="text-[10px] font-mono text-slate-500">Pruned functions</span>
        </div>
      </div>

      {/* Filter and Search Bar with Neo-brutalist styling */}
      <div className="relative p-4 rounded-xl bg-white/95 border border-slate-900/30 shadow-[2px_2px_0px_#141414]">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="relative w-full md:w-88">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search by function name or hex address (0x...)"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg text-xs font-mono bg-[#efece6]/50 border border-slate-900 text-slate-900 placeholder-slate-500 focus:bg-white focus:outline-hidden focus:ring-1 focus:ring-slate-900 shadow-[1px_1px_0px_#141414]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto font-mono text-xs">
            {/* Classification filter */}
            <div className="flex items-center space-x-1.5">
              <span className="text-slate-600 font-bold uppercase text-[11px]">Type:</span>
              <select
                value={classFilter}
                onChange={(e) => setClassFilter(e.target.value)}
                className="py-1.5 px-3 rounded-lg text-xs font-mono bg-white border border-slate-900 text-slate-900 shadow-[1px_1px_0px_#141414] focus:outline-hidden"
              >
                <option value="all">All ({result.ranked_diffs.length})</option>
                <option value="changed-semantic">Semantic ({summary.changed_semantic_count})</option>
                <option value="changed-cosmetic">Cosmetic ({summary.changed_cosmetic_count})</option>
                <option value="identical">Identical ({summary.identical_count})</option>
                <option value="added">Added ({summary.unmatched_b_count})</option>
                <option value="removed">Removed ({summary.unmatched_a_count})</option>
              </select>
            </div>

            {/* Security tag filter */}
            <div className="flex items-center space-x-1.5">
              <span className="text-slate-600 font-bold uppercase text-[11px]">Tag:</span>
              <select
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
                className="py-1.5 px-3 rounded-lg text-xs font-mono bg-white border border-slate-900 text-slate-900 shadow-[1px_1px_0px_#141414] focus:outline-hidden"
              >
                <option value="all">All Tags</option>
                <option value="added_bounds_check">Added Bounds Check</option>
                <option value="added_null_error_check">Added Null Check</option>
                <option value="integer_width_signedness">Integer Width/Sign</option>
                <option value="replaced_unsafe_call">Replaced Unsafe Call</option>
                <option value="new_early_exit">New Early Exit</option>
              </select>
            </div>

            {/* Sort By */}
            <div className="flex items-center space-x-1.5">
              <span className="text-slate-600 font-bold uppercase text-[11px]">Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="py-1.5 px-3 rounded-lg text-xs font-mono bg-white border border-slate-900 text-slate-900 shadow-[1px_1px_0px_#141414] focus:outline-hidden"
              >
                <option value="score">Patch Likelihood</option>
                <option value="rank">Suspicious Rank</option>
                <option value="sim">Lowest Similarity</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Virtualized Functions Table */}
      <div className="relative rounded-2xl border border-slate-900 bg-white shadow-[3px_3px_0px_#141414] overflow-hidden">
        {/* Table Column Headers */}
        <div className="grid grid-cols-12 gap-2 px-6 py-3.5 bg-[#efece6] border-b border-slate-900 text-[11px] font-mono font-bold text-slate-900 uppercase tracking-wider select-none">
          <div className="col-span-1">Rank</div>
          <div className="col-span-2">Classification</div>
          <div className="col-span-3">Baseline Function</div>
          <div className="col-span-3">Patched Function</div>
          <div className="col-span-1 text-right">Similarity</div>
          <div className="col-span-2 text-right">Security Tags / Action</div>
        </div>

        {filteredFunctions.length === 0 ? (
          <div className="py-20 text-center font-mono text-slate-500 text-xs">
            // No functions match current search and filter criteria.
          </div>
        ) : (
          <div
            ref={parentRef}
            className="overflow-auto max-h-[620px] divide-y divide-stone-200"
          >
            <div
              style={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                width: "100%",
                position: "relative",
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const fn = filteredFunctions[virtualRow.index];
                return (
                  <div
                    key={virtualRow.index}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    onClick={() => onSelectFunction(fn)}
                    className="grid grid-cols-12 gap-2 px-6 py-2.5 items-center text-xs hover:bg-[#efece6]/60 cursor-pointer transition-colors"
                  >
                    {/* Rank */}
                    <div className="col-span-1 flex items-center space-x-1">
                      {fn.rank > 0 ? (
                        <span className="font-extrabold font-mono text-xs px-2 py-0.5 rounded bg-rose-600 text-white shadow-[1px_1px_0px_#141414]">
                          #{fn.rank}
                        </span>
                      ) : (
                        <span className="text-slate-400 font-mono text-xs">-</span>
                      )}
                    </div>

                    {/* Classification */}
                    <div className="col-span-2">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded font-mono text-[10px] font-bold border ${getBadgeStyle(
                          fn.classification
                        )}`}
                      >
                        {fn.classification}
                      </span>
                    </div>

                    {/* Baseline Function */}
                    <div className="col-span-3 truncate">
                      <div className="font-mono font-bold text-slate-900 truncate">
                        {fn.name_a}
                      </div>
                      <div className="text-[10px] font-mono text-slate-500">
                        {fn.addr_a ? `0x${fn.addr_a.toString(16)}` : "-"}
                      </div>
                    </div>

                    {/* Patched Function */}
                    <div className="col-span-3 truncate">
                      <div className="font-mono font-bold text-slate-900 truncate">
                        {fn.name_b}
                      </div>
                      <div className="text-[10px] font-mono text-slate-500">
                        {fn.addr_b ? `0x${fn.addr_b.toString(16)}` : "-"}
                      </div>
                    </div>

                    {/* Similarity */}
                    <div className="col-span-1 text-right font-mono font-bold text-slate-900">
                      {(fn.similarity * 100).toFixed(1)}%
                    </div>

                    {/* Security Tags & Button */}
                    <div className="col-span-2 flex items-center justify-end space-x-2">
                      {fn.security_tags.length > 0 && (
                        <span
                          title={fn.security_tags.map((t) => t.description).join("; ")}
                          className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-50 text-rose-800 border border-rose-300"
                        >
                          {fn.security_tags.length} TAGS
                        </span>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectFunction(fn);
                        }}
                        className="group relative inline-flex items-center space-x-1 px-3 py-1 font-mono text-[11px] font-bold uppercase tracking-wider text-slate-900 border border-slate-900 bg-white hover:bg-slate-900 hover:text-white shadow-[1px_1px_0px_#141414] active:shadow-none transition-all cursor-pointer"
                      >
                        <span>Diff View</span>
                        <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
