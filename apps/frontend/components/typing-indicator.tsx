"use client";

import { Bot } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export function TypingIndicator({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2 text-muted-foreground text-sm", className)}>
      <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="flex items-center gap-1 px-3 py-2 rounded-2xl bg-muted">
        <span className="h-1.5 w-1.5 rounded-full bg-foreground/60 animate-pulse-dot" style={{ animationDelay: "0s" }} />
        <span className="h-1.5 w-1.5 rounded-full bg-foreground/60 animate-pulse-dot" style={{ animationDelay: "0.2s" }} />
        <span className="h-1.5 w-1.5 rounded-full bg-foreground/60 animate-pulse-dot" style={{ animationDelay: "0.4s" }} />
      </div>
    </div>
  );
}

export function useAutoScroll(deps: unknown[]) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [stickToBottom, setStickToBottom] = useState(true);

  useEffect(() => {
    if (!ref.current || !stickToBottom) return;
    ref.current.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, deps);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onScroll = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      setStickToBottom(atBottom);
    };
    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  return { ref, stickToBottom };
}
