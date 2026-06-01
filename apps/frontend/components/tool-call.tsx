"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Loader2, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ToolCallRecord {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  pending?: boolean;
}

const friendlyNames: Record<string, string> = {
  k8s_list_pods: "List pods",
  k8s_get_pod_logs: "Fetch pod logs",
  k8s_describe_pod: "Describe pod",
  k8s_list_deployments: "List deployments",
  prom_query: "Query Prometheus",
  prom_query_range: "Query Prometheus (range)",
  loki_query: "Query Loki logs",
};

export function ToolCallCard({ tool }: { tool: ToolCallRecord }) {
  const [open, setOpen] = useState(false);
  const friendly = friendlyNames[tool.name] || tool.name;

  return (
    <div className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/5 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-amber-500/10 transition-colors"
      >
        {open ? (
          <ChevronDown className="h-3 w-3 text-amber-300 shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 text-amber-300 shrink-0" />
        )}
        <Wrench className="h-3 w-3 text-amber-300 shrink-0" />
        <span className="text-xs font-mono text-amber-200">{friendly}</span>
        {Object.keys(tool.args).length > 0 && (
          <span className="text-[10px] text-amber-300/60 font-mono truncate">
            ({Object.entries(tool.args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ")})
          </span>
        )}
        <div className="flex-1" />
        {tool.pending && !tool.result && (
          <Loader2 className="h-3 w-3 text-amber-300 animate-spin" />
        )}
        {tool.result && (
          <span className="text-[10px] text-amber-300/60">
            {tool.result.length > 1000 ? `${(tool.result.length / 1000).toFixed(1)}k chars` : `${tool.result.length} chars`}
          </span>
        )}
      </button>
      {open && tool.result && (
        <pre className="px-3 py-2 text-[10px] text-amber-200/80 bg-black/30 border-t border-amber-500/20 overflow-x-auto max-h-80 scrollbar-thin">
          {tool.result}
        </pre>
      )}
    </div>
  );
}
