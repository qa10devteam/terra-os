"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useAuthFetch } from "@/lib/api-v2";

// ── Colour constants ───────────────────────────────────────────────────────────
const INFO = '#3b82f6';

interface Message {
  role: "user" | "assistant";
  content: string;
  ts?: string;
}

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEnd = useRef<HTMLDivElement>(null);
  const authFetch = useAuthFetch();

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const createSession = useCallback(async () => {
    if (sessionId) return sessionId;
    const data = await authFetch("/api/v2/chat/sessions", {
      method: "POST",
      body: JSON.stringify({
        tenant_id: "default",
        page_context: window.location.pathname,
      }),
    });
    setSessionId(data.session_id);
    return data.session_id;
  }, [sessionId, authFetch]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const sid = await createSession();
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v2/chat/sessions/${sid}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
          body: JSON.stringify({ message: userMsg }),
        }
      );

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No reader");

      const decoder = new TextDecoder();
      let assistantContent = "";

      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "token") {
              assistantContent += event.content;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: assistantContent,
                };
                return updated;
              });
            }
          } catch {}
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Przepraszam, wystąpił błąd. Spróbuj ponownie." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-accent-info px-5 py-3 text-earth-50 shadow-token-lg hover:opacity-90 transition-all"
      >
        <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <span className="font-medium text-sm">budos</span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col w-[380px] h-[520px] rounded-token-xl border border-earth-800 bg-earth-950 shadow-token-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-earth-800 bg-earth-900">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-accent-success animate-pulse-soft" />
          <span className="font-semibold text-earth-100 text-sm">budos</span>
          <span className="text-xs text-earth-400">AI asystent</span>
        </div>
        <button onClick={() => setOpen(false)} className="text-earth-500 hover:text-earth-200 transition-colors">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-earth-500 text-sm mt-8">
            <p className="text-lg mb-2">👋</p>
            <p>Cześć! Jestem <strong>budos</strong>.</p>
            <p className="mt-1">Zapytaj mnie o przetargi, analizy, kosztorysy...</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-token-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-accent-info/20 text-earth-100 border border-accent-info/20"
                  : "bg-earth-800 text-earth-200 border border-earth-700/40"
              }`}
            >
              {msg.content || (
                <span className="inline-flex gap-1">
                  <span className="animate-bounce">.</span>
                  <span className="animate-bounce" style={{ animationDelay: "0.1s" }}>.</span>
                  <span className="animate-bounce" style={{ animationDelay: "0.2s" }}>.</span>
                </span>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEnd} />
      </div>

      {/* Input */}
      <div className="border-t border-earth-800 p-3 bg-earth-900">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Napisz wiadomość..."
            disabled={loading}
            className="input-base flex-1 text-sm disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="rounded-token-lg bg-accent-info px-3 py-2 text-earth-50 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
