"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, Send, Square, Trash2, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MessageBubble } from "@/components/message";
import { Suggestions } from "@/components/suggestions";
import { TypingIndicator, useAutoScroll } from "@/components/typing-indicator";
import { getHealth, streamChat } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/types";

function newId() {
  return Math.random().toString(36).slice(2, 11);
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [health, setHealth] = useState<{ status: string; model: string; llm_configured: boolean } | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const { ref: scrollRef, stickToBottom } = useAutoScroll([messages, isStreaming]);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setHealth({ status: "down", model: "—", llm_configured: false }));
  }, []);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;

      const userMsg: Message = {
        id: newId(),
        role: "user",
        content: trimmed,
        timestamp: Date.now(),
      };
      const assistantId = newId();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        pending: true,
        timestamp: Date.now(),
      };
      setMessages((m) => [...m, userMsg, assistantMsg]);
      setInput("");

      const abort = new AbortController();
      abortRef.current = abort;
      setIsStreaming(true);

      const history = [...messages, userMsg]
        .filter((m) => m.role === "user" || m.role === "assistant")
        .filter((m) => !m.pending && !m.error)
        .map(({ role, content }) => ({ role, content }));

      try {
        await streamChat(history, abort.signal, {
          onToken: (token) => {
            setMessages((curr) =>
              curr.map((m) => (m.id === assistantId ? { ...m, content: m.content + token } : m))
            );
          },
          onCitations: (citations) => {
            setMessages((curr) =>
              curr.map((m) => (m.id === assistantId ? { ...m, citations } : m))
            );
          },
          onToolCall: (tool) => {
            setMessages((curr) =>
              curr.map((m) => {
                if (m.id !== assistantId) return m;
                const existing = m.toolCalls || [];
                if (existing.some((t) => t.id === tool.id)) return m;
                return { ...m, toolCalls: [...existing, tool] };
              })
            );
          },
          onToolResult: (tool) => {
            setMessages((curr) =>
              curr.map((m) => {
                if (m.id !== assistantId) return m;
                const existing = m.toolCalls || [];
                return {
                  ...m,
                  toolCalls: existing.map((t) => (t.id === tool.id ? { ...t, result: tool.result, pending: false } : t)),
                };
              })
            );
          },
          onDone: (model) => {
            setMessages((curr) =>
              curr.map((m) =>
                m.id === assistantId ? { ...m, pending: false, model: model || m.model } : m
              )
            );
            setIsStreaming(false);
            abortRef.current = null;
          },
          onError: (msg) => {
            setMessages((curr) =>
              curr.map((m) =>
                m.id === assistantId ? { ...m, content: msg, error: true, pending: false } : m
              )
            );
            setIsStreaming(false);
            abortRef.current = null;
          },
        });
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Network error";
        setMessages((curr) =>
          curr.map((m) => (m.id === assistantId ? { ...m, content: msg, error: true, pending: false } : m))
        );
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, messages]
  );

  const stop = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setMessages((curr) => curr.map((m) => (m.pending ? { ...m, pending: false } : m)));
  };

  const clear = () => {
    if (isStreaming) stop();
    setMessages([]);
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-background to-[hsl(222,47%,3%)]">
      <header className="border-b border-white/5 backdrop-blur bg-background/70 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <Activity className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h2 className="text-sm font-semibold">DevOps Copilot</h2>
              <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    health?.status === "ok" ? "bg-green-400" :
                    health?.status === "degraded" ? "bg-yellow-400" : "bg-red-400"
                  )}
                />
                <span>
                  {health ? (health.llm_configured ? health.model : "LLM not configured") : "Connecting…"}
                </span>
              </div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={clear}
            disabled={messages.length === 0}
            className="text-muted-foreground hover:text-foreground"
            title="Clear chat"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
        {messages.length === 0 ? (
          <Suggestions onPick={send} />
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {isStreaming && messages[messages.length - 1]?.content === "" && <TypingIndicator />}
          </div>
        )}
        {!stickToBottom && messages.length > 0 && (
          <button
            onClick={() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })}
            className="fixed bottom-24 left-1/2 -translate-x-1/2 h-8 w-8 rounded-full bg-muted border border-white/10 flex items-center justify-center hover:bg-muted/80 transition"
            title="Scroll to bottom"
          >
            <ArrowDown className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="border-t border-white/5 bg-background/70 backdrop-blur">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="max-w-3xl mx-auto px-4 py-4"
        >
          <div className="relative flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              placeholder={health?.llm_configured ? "Ask about your cluster…" : "Configure OPENROUTER_API_KEY in copilot-backend/.env"}
              rows={1}
              disabled={!health?.llm_configured}
              className="flex-1 resize-none bg-muted border border-white/10 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/30 placeholder:text-muted-foreground disabled:opacity-50 max-h-40 scrollbar-thin"
              style={{ minHeight: "44px" }}
            />
            {isStreaming ? (
              <Button type="button" onClick={stop} size="icon" className="h-11 w-11 rounded-full" variant="destructive">
                <Square className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                type="submit"
                size="icon"
                className="h-11 w-11 rounded-full"
                disabled={!input.trim() || !health?.llm_configured}
              >
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
          <p className="text-[10px] text-muted-foreground mt-2 text-center">
            Powered by OpenRouter · Llama 3.3 70B (free tier) · Read{" "}
            <a href="https://github.com" className="underline hover:text-foreground">
              the runbook
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}
