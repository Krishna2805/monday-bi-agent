import React, { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, Info } from "lucide-react";

export function CaveatsPanel({ caveats }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!caveats || caveats.length === 0) return null;

  return (
    <div className="mx-6 my-2 glass-card rounded-xl border border-amber-500/20 overflow-hidden transition-all duration-200">
      {/* Header Bar */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-2.5 flex items-center justify-between bg-amber-500/10 hover:bg-amber-500/15 transition-colors cursor-pointer text-left"
      >
        <div className="flex items-center gap-2 text-xs font-medium text-amber-300">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <span>Active Data Quality Caveats ({caveats.length})</span>
        </div>
        <div className="flex items-center gap-1 text-slate-400 text-xs">
          <span className="hidden sm:inline">
            {isOpen ? "Hide details" : "Show details"}
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </div>
      </button>

      {/* Collapsible Content */}
      {isOpen && (
        <div className="p-4 bg-slate-950/60 border-t border-amber-500/10 text-xs space-y-2">
          <p className="text-slate-400 flex items-center gap-1.5 font-medium mb-2">
            <Info className="w-3.5 h-3.5 text-cyan-400" />
            The following data limitations were identified in your Monday.com boards:
          </p>
          <ul className="space-y-1.5 pl-1">
            {caveats.map((note, index) => (
              <li
                key={index}
                className="flex items-start gap-2 text-amber-200/90 leading-relaxed"
              >
                <span className="text-amber-400 font-bold">•</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
