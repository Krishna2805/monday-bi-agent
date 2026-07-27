import React from "react";
import { Sparkles, Activity, FileText, Database } from "lucide-react";

export function Header({ onGenerateBrief, isConnected, modelName }) {
  return (
    <header className="glass-panel sticky top-0 z-30 px-6 py-4 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 shadow-xl">
      {/* Brand & Logo */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 p-0.5 shadow-lg shadow-cyan-500/20">
          <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" />
          </div>
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            Monday.com BI Agent
            <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              Prototype
            </span>
          </h1>
          <p className="text-xs text-slate-400 flex items-center gap-2">
            <Database className="w-3 h-3 text-slate-500" />
            Geospatial & Drone Survey Business Intelligence
          </p>
        </div>
      </div>

      {/* Status & Actions */}
      <div className="flex items-center gap-3">
        {/* Status Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
          <Activity
            className={`w-3.5 h-3.5 ${
              isConnected ? "text-emerald-400" : "text-amber-400"
            }`}
          />
          <span className="text-slate-300">
            {isConnected ? "Connected to Monday.com" : "Connecting..."}
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400 font-mono">
            {modelName || "gemini-3.6-flash"}
          </span>
        </div>

        {/* Executive Brief Button */}
        <button
          onClick={onGenerateBrief}
          className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-medium shadow-md shadow-cyan-600/20 transition-all duration-200 cursor-pointer active:scale-95"
        >
          <FileText className="w-3.5 h-3.5" />
          Generate Executive Brief
        </button>
      </div>
    </header>
  );
}
