import React from "react";
import { Link } from "react-router-dom";
import { GitCompare, Home } from "lucide-react";

interface NavbarProps {
  onNewAnalysis: () => void;
  hasResult: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onNewAnalysis, hasResult }) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-stone-200/90 bg-white/85 backdrop-blur-md shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link
          to="/"
          className="flex items-center space-x-3 cursor-pointer select-none group"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-700 via-indigo-600 to-indigo-800 flex items-center justify-center text-white shadow-sm shadow-indigo-600/20 group-hover:scale-105 transition-transform">
            <GitCompare className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-lg tracking-tight text-slate-900 group-hover:text-indigo-700 transition-colors">
                PatchLens
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                v0.1.0
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Binary Diffing & Security Patch Analyzer
            </p>
          </div>
        </Link>

        <div className="flex items-center space-x-3">
          <Link
            to="/"
            className="flex items-center space-x-1.5 text-xs font-medium text-slate-600 hover:text-indigo-700 px-3 py-1.5 rounded-lg hover:bg-stone-100 transition-colors"
          >
            <Home className="w-3.5 h-3.5" />
            <span>Home</span>
          </Link>

          {hasResult && (
            <button
              onClick={onNewAnalysis}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-stone-300 hover:border-stone-400 bg-white hover:bg-stone-50 text-slate-800 shadow-2xs hover:shadow-xs transition-all active:scale-95"
            >
              + New Analysis
            </button>
          )}

          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>Engine Ready</span>
          </div>
        </div>
      </div>
    </header>
  );
};
