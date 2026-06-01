import type { Message } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

import type { Citation } from "./types";

export interface StreamHandlers {
  onToken: (token: string) => void;
  onDone: (model?: string, finishReason?: string) => void;
  onError: (message: string) => void;
  onCitations?: (citations: Citation[]) => void;
  onToolCall?: (tool: { id: string; name: string; args: Record<string, unknown>; pending: boolean }) => void;
  onToolResult?: (tool: { id: string; name: string; args: Record<string, unknown>; result?: string; pending: boolean }) => void;
}

export async function streamChat(
  messages: Pick<Message, "role" | "content">[],
  signal: AbortSignal,
  handlers: StreamHandlers
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, stream: true }),
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {}
    handlers.onError(detail);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const payload = trimmed.slice(5).trim();
      if (!payload) continue;
        try {
        const chunk = JSON.parse(payload);
        if (chunk.type === "token" && chunk.content) {
          handlers.onToken(chunk.content);
        } else if (chunk.type === "done") {
          handlers.onDone(chunk.model, chunk.finish_reason);
        } else if (chunk.type === "error") {
          handlers.onError(chunk.content || "Unknown error");
        } else if (chunk.type === "rag_citation" && chunk.results) {
          handlers.onCitations?.(chunk.results);
        } else if (chunk.type === "tool_call" && chunk.tool_name && chunk.tool_call_id) {
          handlers.onToolCall?.({
            id: chunk.tool_call_id,
            name: chunk.tool_name,
            args: chunk.tool_args || {},
            pending: true,
          });
        } else if (chunk.type === "tool_result" && chunk.tool_name && chunk.tool_call_id) {
          handlers.onToolResult?.({
            id: chunk.tool_call_id,
            name: chunk.tool_name,
            args: {},
            result: chunk.content,
            pending: false,
          });
        }
      } catch (e) {
        console.warn("Failed to parse SSE chunk", e);
      }
    }
  }
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
