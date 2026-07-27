import React from "react";
import ReactMarkdown from "react-markdown";
import { Bot, User, AlertTriangle } from "lucide-react";

export function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 my-4 ${
        isUser ? "justify-end" : "justify-start"
      } animate-in fade-in slide-in-from-bottom-2 duration-300`}
    >
      {/* Bot Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-600 p-0.5 flex-shrink-0 shadow-md">
          <div className="w-full h-full bg-slate-900 rounded-[6px] flex items-center justify-center">
            <Bot className="w-4 h-4 text-cyan-400" />
          </div>
        </div>
      )}

      {/* Message Content Bubble */}
      <div
        className={`max-w-[85%] rounded-2xl px-5 py-3.5 shadow-lg border text-sm leading-relaxed ${
          isUser
            ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white border-cyan-500/30 rounded-tr-none"
            : "glass-panel text-slate-100 border-slate-800 rounded-tl-none"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-headings:text-white prose-strong:text-cyan-300 prose-ul:my-2 prose-li:my-0.5">
            <ReactMarkdown
              components={{
                // Custom renderer for lines starting with ⚠️ Data note:
                p: ({ children }) => {
                  const text = String(children);
                  if (text.includes("⚠️ Data note:") || text.includes("⚠️ Data Note:")) {
                    return (
                      <p className="my-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                        <span>{children}</span>
                      </p>
                    );
                  }
                  return <p className="mb-3 last:mb-0">{children}</p>;
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-slate-800 p-0.5 flex-shrink-0 border border-slate-700 shadow-md">
          <div className="w-full h-full bg-slate-900 rounded-[6px] flex items-center justify-center">
            <User className="w-4 h-4 text-slate-400" />
          </div>
        </div>
      )}
    </div>
  );
}
