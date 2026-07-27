import React from "react";
import { Sparkles, TrendingUp, DollarSign, Clock, Layers } from "lucide-react";

const STARTER_QUERIES = [
  {
    icon: TrendingUp,
    label: "Mining Pipeline",
    query: "How's our Mining pipeline looking?",
  },
  {
    icon: DollarSign,
    label: "Total AR Outstanding",
    query: "What's our total AR outstanding across all work orders?",
  },
  {
    icon: Layers,
    label: "Revenue by Sector",
    query: "Show me revenue breakdown by sector",
  },
  {
    icon: Clock,
    label: "Delayed Projects",
    query: "Which projects are currently delayed or on pause?",
  },
  {
    icon: Sparkles,
    label: "High Prob Deals",
    query: "List all high probability deals closing this month",
  },
];

export function StarterChips({ onSelectQuery }) {
  return (
    <div className="my-6 px-4">
      <p className="text-xs text-slate-400 font-medium mb-3 flex items-center justify-center gap-1.5">
        <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
        Starter Queries for Executive Leadership
      </p>
      <div className="flex flex-wrap items-center justify-center gap-2 max-w-3xl mx-auto">
        {STARTER_QUERIES.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              onClick={() => onSelectQuery(item.query)}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl glass-card hover:bg-slate-800/80 hover:border-cyan-500/30 text-slate-200 hover:text-white text-xs font-medium transition-all duration-200 cursor-pointer active:scale-95 shadow-sm"
            >
              <Icon className="w-3.5 h-3.5 text-cyan-400" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
