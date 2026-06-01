"use client";

import { Sparkles } from "lucide-react";
import { SUGGESTIONS } from "@/lib/prompts";

export function Suggestions({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center h-12 w-12 rounded-2xl bg-primary/10 mb-4">
          <Sparkles className="h-6 w-6 text-primary" />
        </div>
        <h1 className="text-3xl font-semibold tracking-tight mb-2">DevOps Copilot</h1>
        <p className="text-muted-foreground text-sm max-w-md mx-auto">
          Ask about your Kubernetes cluster, query metrics, search logs, and follow runbooks — all in natural language.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onPick(s)}
            className="text-left text-sm p-3 rounded-xl bg-muted/50 border border-white/5 hover:border-primary/30 hover:bg-muted transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
