import React, { useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  ShieldAlert,
  Search,
  Network,
  Download,
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
    estimateSize: () => 58,
    overscan: 10,
  });

  // WCAG AA Compliant accessible badge styles
  const getBadgeStyle = (classification: string) => {
    switch (classification) {
      case "changed-semantic":
        return "bg-amber-50 text-amber-900 border-amber-300";
      case "changed-cosmetic":
        return "bg-sky-50 text-sky-900 border-sky-300";
      case "added":
        return "bg-emerald-50 text-emerald-900 border-emerald-300";
      case "removed":
        return "bg-rose-50 text-rose-900 border-rose-300";
      default:
        return "bg-stone-100 text-slate-700 border-stone-200";
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Top Banner & Export Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-stone-200">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <span>Diff Results & Security Localization</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-stone-100 text-slate-600 border border-stone-200 font-mono">
              Pair: {result.pair_hash.slice(0, 16)}...
            </span>
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Matched {summary.matched_count} functions across binaries with {summary.top_patch_candidates_count} suspicious security patch candidates.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={onToggleCallGraph}
            className={`inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
              showCallGraph
                ? "bg-indigo-700 text-white border-indigo-700 shadow-sm shadow-indigo-600/20"
                : "bg-white text-slate-700 border-stone-300 hover:bg-stone-50 hover:border-stone-400 shadow-2xs"
            }`}
          >
            <Network className="w-4 h-4" />
            <span>{showCallGraph ? "View Functions Table" : "Match Explorer (Call Graph)"}</span>
          </button>

          <a
            href={getExportJsonUrl(result.id)}
            download
            className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-white text-slate-700 border border-stone-300 hover:bg-stone-50 hover:border-stone-400 shadow-2xs transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>JSON</span>
          </a>

          <a
            href={getExportMarkdownUrl(result.id)}
            download
            className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-white text-slate-700 border border-stone-300 hover:bg-stone-50 hover:border-stone-400 shadow-2xs transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Markdown</span>
          </a>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="p-4 rounded-2xl bg-white border border-stone-200 shadow-card">
          <span className="text-xs text-slate-500 font-medium">Total Baseline</span>
          <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums">
            {summary.total_functions_a}
          </div>
          <span className="text-[10px] text-slate-400">Functions</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-stone-200 shadow-card">
          <span className="text-xs text-slate-500 font-medium">Matched Pairs</span>
          <div className="text-2xl font-bold text-indigo-700 mt-1 tabular-nums">
            {summary.matched_count}
          </div>
          <span className="text-[10px] text-indigo-600 font-medium">
            {summary.total_functions_a > 0
              ? `${((summary.matched_count / summary.total_functions_a) * 100).toFixed(1)}% match rate`
              : "0%"}
          </span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-rose-200 shadow-card">
          <span className="text-xs text-rose-700 font-semibold flex items-center space-x-1">
            <span>Semantic Changes</span>
            <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
          </span>
          <div className="text-2xl font-bold text-rose-700 mt-1 tabular-nums">
            {summary.changed_semantic_count}
          </div>
          <span className="text-[10px] text-rose-500">Logic modified</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-amber-200 shadow-card">
          <span className="text-xs text-amber-800 font-medium">Cosmetic Only</span>
          <div className="text-2xl font-bold text-amber-800 mt-1 tabular-nums">
            {summary.changed_cosmetic_count}
          </div>
          <span className="text-[10px] text-amber-600">Regs / layout noise</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-emerald-200 shadow-card">
          <span className="text-xs text-emerald-800 font-medium">Added</span>
          <div className="text-2xl font-bold text-emerald-800 mt-1 tabular-nums">
            {summary.unmatched_b_count}
          </div>
          <span className="text-[10px] text-emerald-600">New functions</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-stone-200 shadow-card">
          <span className="text-xs text-slate-600 font-medium">Removed</span>
          <div className="text-2xl font-bold text-slate-800 mt-1 tabular-nums">
            {summary.unmatched_a_count}
          </div>
          <span className="text-[10px] text-slate-400">Pruned functions</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-white border border-stone-200 shadow-card">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name or address (0x...)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl text-xs bg-stone-50 border border-stone-200 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-600"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Classification filter */}
          <div className="flex items-center space-x-1 text-xs">
            <span className="text-slate-500 font-medium">Type:</span>
            <select
              value={classFilter}
              onChange={(e) => setClassFilter(e.target.value)}
              className="py-1.5 px-2.5 rounded-lg text-xs bg-stone-50 border border-stone-200 text-slate-800 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-600"
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
          <div className="flex items-center space-x-1 text-xs">
            <span className="text-slate-500 font-medium">Security Tag:</span>
            <select
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
              className="py-1.5 px-2.5 rounded-lg text-xs bg-stone-50 border border-stone-200 text-slate-800 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-600"
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
          <div className="flex items-center space-x-1 text-xs">
            <span className="text-slate-500 font-medium">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="py-1.5 px-2.5 rounded-lg text-xs bg-stone-50 border border-stone-200 text-slate-800 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-600"
            >
              <option value="score">Patch Likelihood</option>
              <option value="rank">Suspicious Rank</option>
              <option value="sim">Lowest Similarity</option>
            </select>
          </div>
        </div>
      </div>

      {/* Virtualized Functions Table */}
      <div className="rounded-2xl border border-stone-200 bg-white overflow-hidden shadow-card">
        <div className="grid grid-cols-12 gap-2 px-6 py-3 bg-stone-50 border-b border-stone-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
          <div className="col-span-1">Rank</div>
          <div className="col-span-2">Classification</div>
          <div className="col-span-3">Baseline Function</div>
          <div className="col-span-3">Patched Function</div>
          <div className="col-span-1 text-right">Similarity</div>
          <div className="col-span-2 text-right">Security Tags / Action</div>
        </div>

        {filteredFunctions.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm">
            No functions match current search and filter criteria.
          </div>
        ) : (
          <div
            ref={parentRef}
            className="overflow-auto max-h-[600px] divide-y divide-stone-100"
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
                    className="grid grid-cols-12 gap-2 px-6 py-2.5 items-center text-xs hover:bg-indigo-50/40 cursor-pointer transition-colors"
                  >
                    {/* Rank */}
                    <div className="col-span-1 flex items-center space-x-1">
                      {fn.rank > 0 ? (
                        <span className="font-extrabold text-xs px-2 py-0.5 rounded-md bg-rose-600 text-white shadow-2xs">
                          #{fn.rank}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-xs">-</span>
                      )}
                    </div>

                    {/* Classification */}
                    <div className="col-span-2">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${getBadgeStyle(
                          fn.classification
                        )}`}
                      >
                        {fn.classification}
                      </span>
                    </div>

                    {/* Baseline Function */}
                    <div className="col-span-3 truncate">
                      <div className="font-mono font-semibold text-slate-900 truncate">
                        {fn.name_a}
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        {fn.addr_a ? `0x${fn.addr_a.toString(16)}` : "-"}
                      </div>
                    </div>

                    {/* Patched Function */}
                    <div className="col-span-3 truncate">
                      <div className="font-mono font-semibold text-slate-900 truncate">
                        {fn.name_b}
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        {fn.addr_b ? `0x${fn.addr_b.toString(16)}` : "-"}
                      </div>
                    </div>

                    {/* Similarity */}
                    <div className="col-span-1 text-right font-mono font-semibold text-slate-800">
                      {(fn.similarity * 100).toFixed(1)}%
                    </div>

                    {/* Security Tags & Button */}
                    <div className="col-span-2 flex items-center justify-end space-x-2">
                      {fn.security_tags.length > 0 && (
                        <span
                          title={fn.security_tags.map((t) => t.description).join("; ")}
                          className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200"
                        >
                          {fn.security_tags.length} TAGS
                        </span>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectFunction(fn);
                        }}
                        className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-stone-100 hover:bg-indigo-700 hover:text-white text-slate-700 border border-stone-200 hover:border-indigo-700 transition-all shadow-2xs active:scale-95"
                      >
                        Diff View
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
