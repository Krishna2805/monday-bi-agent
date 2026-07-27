import React, { useState, useEffect, useRef } from "react";
import { Header } from "./components/Header";
import { MessageBubble } from "./components/MessageBubble";
import { CaveatsPanel } from "./components/CaveatsPanel";
import { StarterChips } from "./components/StarterChips";
import { ChatInput } from "./components/ChatInput";
import { sendChatMessage, getBackendHealth } from "./api/chat";
import { Sparkles, Loader2, RefreshCw } from "lucide-react";

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I am your **Monday.com Business Intelligence Agent**. I have direct access to your Work Orders and Deals Pipeline boards.\n\nAsk me anything about pipeline value, weighted forecasts, win rates, revenue collections, AR outstanding, or project execution status!",
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [caveats, setCaveats] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [modelName, setModelName] = useState("");
  const messagesEndRef = useRef(null);

  // Check health on mount
  useEffect(() => {
    async function checkHealth() {
      const health = await getBackendHealth();
      if (health && health.status === "ok") {
        setIsConnected(true);
        setModelName(health.model || "llama-3.3-70b-versatile");
      } else {
        setIsConnected(false);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Extract data quality notes from agent response text
  const extractCaveats = (replyText) => {
    const lines = replyText.split("\n");
    const newNotes = [];
    lines.forEach((line) => {
      if (line.includes("⚠️ Data note:") || line.includes("⚠️ Data Note:")) {
        const cleaned = line
          .replace("⚠️ Data note:", "")
          .replace("⚠️ Data Note:", "")
          .trim();
        if (cleaned && !caveats.includes(cleaned)) {
          newNotes.push(cleaned);
        }
      }
    });
    if (newNotes.length > 0) {
      setCaveats((prev) => [...new Set([...prev, ...newNotes])]);
    }
  };

  const handleSendMessage = async (userQuery) => {
    const userMsg = { role: "user", content: userQuery };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setIsLoading(true);

    try {
      const reply = await sendChatMessage(updatedMessages);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      extractCaveats(reply);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ **Connection Error**: ${err.message}. Please verify the backend server is running.`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Executive Brief Generator
  const handleGenerateBrief = () => {
    handleSendMessage(
      "Generate an executive leadership briefing summarizing sales pipeline health, revenue collections, AR priority accounts, and project execution status."
    );
  };

  const handleClearChat = () => {
    setMessages([
      {
        role: "assistant",
        content:
          "Chat session cleared. How can I assist you with your Monday.com business data?",
      },
    ]);
    setCaveats([]);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between text-slate-100 font-sans selection:bg-cyan-500 selection:text-white">
      {/* Top Navigation Header */}
      <Header
        onGenerateBrief={handleGenerateBrief}
        isConnected={isConnected}
        modelName={modelName}
      />

      {/* Main Chat Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto flex flex-col justify-between p-4 sm:p-6">
        {/* Caveats Notification Panel */}
        <CaveatsPanel caveats={caveats} />

        {/* Message Feed */}
        <div className="flex-1 my-4 space-y-4">
          {messages.map((msg, index) => (
            <MessageBubble key={index} message={msg} />
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex items-center gap-3 my-4 animate-pulse">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-600 p-0.5 shadow-md">
                <div className="w-full h-full bg-slate-900 rounded-[6px] flex items-center justify-center">
                  <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                </div>
              </div>
              <div className="glass-panel px-4 py-3 rounded-2xl border-slate-800 text-xs text-slate-400 flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                Querying Monday.com boards & calculating analytics...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Starter Query Chips (shown when message count is small) */}
        {messages.length <= 3 && !isLoading && (
          <StarterChips onSelectQuery={handleSendMessage} />
        )}

        {/* Reset Session Button */}
        {messages.length > 2 && (
          <div className="flex justify-center my-2">
            <button
              onClick={handleClearChat}
              className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3 h-3" />
              Reset Conversation
            </button>
          </div>
        )}
      </main>

      {/* Sticky Bottom Prompt Input */}
      <ChatInput
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        onGenerateBrief={handleGenerateBrief}
      />
    </div>
  );
}
