export type Role = "system" | "user" | "assistant";

export interface Citation {
  source: string;
  section?: string;
  similarity: number;
}

export interface ToolCallRecord {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  pending?: boolean;
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  pending?: boolean;
  error?: boolean;
  model?: string;
  timestamp: number;
  citations?: Citation[];
  toolCalls?: ToolCallRecord[];
}

export interface ChatChunk {
  type: "token" | "done" | "error" | "tool_call" | "tool_result" | "rag_citation";
  content?: string;
  finish_reason?: string;
  model?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  tool_call_id?: string;
  results?: Citation[];
}
