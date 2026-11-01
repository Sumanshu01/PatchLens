import React from "react";
import { Link } from "react-router-dom";
import { Home, RefreshCw } from "lucide-react";

interface NavbarProps {
  onNewAnalysis: () => void;
  hasResult: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onNewAnalysis, hasResult }) => {
  return (
    <header className="sticky top-0 z-40 w-full bg-[#efece6]/90 backdrop-blur-md border-b border-stone-900/10 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-[72px] flex items-center justify-between">
        {/* Brand Logo & Version */}
        <Link to="/" className="flex items-center space-x-3.5 group select-none">
          <svg className="w-10 h-10 shrink-0" viewBox="0 0 28 28" fill="none">
            <defs>
              <linearGradient id="logoGradNavbar" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#ffb347" />
                <stop offset="50%" stopColor="#ff5a5f" />
                <stop offset="100%" stopColor="#ff3d8b" />
              </linearGradient>
            </defs>
            <path
              d="M 22 7 L 11 7 A 4 4 0 0 0 7 11 L 7 17 A 4 4 0 0 0 11 21 L 22 21"
              stroke="url(#logoGradNavbar)"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <circle cx="12" cy="14" r="1.5" fill="#141414" />
            <circle cx="17" cy="14" r="1.5" fill="#141414" />
          </svg>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-xl tracking-tight text-slate-900 group-hover:text-indigo-700 transition-colors">
                PatchLens
              </span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-stone-100 text-stone-800 border border-stone-300">
                v0.1.0
              </span>
            </div>
            <p className="text-[11px] font-mono text-slate-500 hidden sm:block">
              Binary Diffing & Security Analyzer
            </p>
          </div>
        </Link>

        {/* Actions Cell */}
        <div className="flex items-center space-x-3">
          <Link
            to="/"
            className="group relative inline-flex items-center space-x-1.5 px-3.5 py-1.5 font-mono text-xs uppercase tracking-wider text-slate-700 hover:text-slate-900 border border-transparent hover:border-slate-900 hover:bg-white hover:shadow-[2px_2px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all duration-150 select-none"
          >
            {/* 4 Maximalist Technical Corner Brackets */}
            <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
            <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
            <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
            <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150" />

            <Home className="w-3.5 h-3.5" />
            <span>Home</span>
          </Link>

          {hasResult && (
            <button
              onClick={onNewAnalysis}
              className="group relative inline-flex items-center space-x-2 px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider text-slate-900 border border-slate-900 bg-white hover:bg-stone-50 shadow-[2px_2px_0px_#141414] hover:shadow-[3px_3px_0px_#141414] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all cursor-pointer"
            >
              {/* 4 Maximalist Technical Corner Brackets */}
              <span className="absolute -top-1 -left-1 w-1.5 h-1.5 border-t border-l border-slate-900 pointer-events-none" />
              <span className="absolute -top-1 -right-1 w-1.5 h-1.5 border-t border-r border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -left-1 w-1.5 h-1.5 border-b border-l border-slate-900 pointer-events-none" />
              <span className="absolute -bottom-1 -right-1 w-1.5 h-1.5 border-b border-r border-slate-900 pointer-events-none" />

              <RefreshCw className="w-3 h-3 text-indigo-700 group-hover:rotate-180 transition-transform duration-300" />
              <span>+ New Analysis</span>
            </button>
          )}

          <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded bg-white/80 border border-stone-300 font-mono text-xs font-semibold text-emerald-800 shadow-2xs backdrop-blur-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Engine Ready</span>
          </div>
        </div>
      </div>
    </header>
  );
};
