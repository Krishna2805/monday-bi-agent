import React, { useState } from "react";
import { Send, Loader2, FileText } from "lucide-react";

export function ChatInput({ onSendMessage, isLoading, onGenerateBrief }) {
  const [input, setInput] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    if (input.trim() === "/report") {
      onGenerateBrief();
      setInput("");
      return;
    }

    onSendMessage(input.trim());
    setInput("");
  };

  return (
    <div className="sticky bottom-0 z-20 p-4 glass-panel border-t border-slate-800">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-center gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about sales pipeline, revenue, AR, or project status... (type /report for executive brief)"
            disabled={isLoading}
            className="w-full pl-4 pr-12 py-3.5 rounded-xl bg-slate-900/90 border border-slate-800 focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20 text-white placeholder-slate-500 text-sm outline-none transition-all duration-200 disabled:opacity-50"
          />
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onGenerateBrief}
            title="Generate Leadership Update Brief (/report)"
            disabled={isLoading}
            className="p-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-all cursor-pointer disabled:opacity-50"
          >
            <FileText className="w-4 h-4 text-cyan-400" />
          </button>

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="p-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white transition-all shadow-md shadow-cyan-500/20 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed active:scale-95 flex items-center justify-center min-w-[48px]"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
