"use client";

import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { Bot, FileText, User2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/types";
import { ToolCallCard } from "@/components/tool-call";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-3 items-start animate-fade-in",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      <div
        className={cn(
          "h-7 w-7 rounded-full flex items-center justify-center shrink-0 mt-1",
          isUser ? "bg-cyan-500/20" : "bg-primary/10"
        )}
      >
        {isUser ? (
          <User2 className="h-4 w-4 text-cyan-300" />
        ) : (
          <Bot className="h-4 w-4 text-primary" />
        )}
      </div>
      <div
        className={cn(
          "max-w-[85%] space-y-1",
          isUser ? "items-end" : "items-start"
        )}
      >
        <div
          className={cn(
            "message-content rounded-2xl px-4 py-3 text-sm",
            isUser
              ? "bg-cyan-500/10 border border-cyan-500/20 text-foreground"
              : "bg-muted border border-white/5 text-foreground"
          )}
        >
          {message.error ? (
            <div className="text-red-400">
              <strong>Error:</strong> {message.content}
            </div>
          ) : message.content ? (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
            >
              {message.content}
            </ReactMarkdown>
          ) : (
            <span className="text-muted-foreground italic">thinking…</span>
          )}
        </div>

        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="w-full max-w-full space-y-1">
            {message.toolCalls.map((tc) => (
              <ToolCallCard key={tc.id} tool={tc} />
            ))}
          </div>
        )}

        {message.citations && message.citations.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-muted/50 px-4 py-3">
            <div className="text-[10px] text-muted-foreground/70 mb-1.5 font-semibold uppercase tracking-wider">
              Sources
            </div>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((c, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-300"
                  title={`similarity: ${(c.similarity * 100).toFixed(0)}%`}
                >
                  <FileText className="h-2.5 w-2.5" />
                  {c.source.split("/").pop()}
                  {c.section ? ` › ${c.section}` : ""}
                </span>
              ))}
            </div>
          </div>
        )}

        {message.model && !isUser && !message.error && (
          <div className="text-[10px] text-muted-foreground/60 font-mono px-1">
            {message.model}
          </div>
        )}
      </div>
    </div>
  );
}
