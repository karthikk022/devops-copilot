import logging
from typing import Any, AsyncIterator, List, Optional

from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError

from .config import Settings
from .models import ChatMessage

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
APP_NAME = "DevOps Copilot"
APP_URL = "https://github.com/karthikk022/devops-copilot"


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=settings.openrouter_api_key,
            default_headers={
                "HTTP-Referer": APP_URL,
                "X-Title": APP_NAME,
            },
        )
        self.primary = settings.llm_model
        self.fallbacks = settings.fallback_models

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.openrouter_api_key
            and self.settings.openrouter_api_key.startswith("sk-or-")
        )

    async def _completion(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[dict]] = None,
        stream: bool = False,
    ) -> Any:
        if not self.configured:
            raise RuntimeError("OPENROUTER_API_KEY not configured")

        models_to_try = [model] if model else [self.primary, *self.fallbacks]
        temp = temperature if temperature is not None else self.settings.llm_temperature
        max_tokens = self.settings.llm_max_tokens

        kwargs: dict[str, Any] = {
            "model": models_to_try[0],
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if stream:
            kwargs["stream_options"] = {"include_usage": True}

        last_error: Optional[Exception] = None
        for m in models_to_try:
            try:
                kwargs["model"] = m
                logger.info(
                    "llm_request",
                    extra={
                        "model": m,
                        "messages": len(messages),
                        "tools": len(tools or []),
                        "stream": stream,
                    },
                )
                return await self.client.chat.completions.create(**kwargs)
            except RateLimitError as e:
                last_error = e
                logger.warning("llm_rate_limit", extra={"model": m, "error": str(e)})
                continue
            except (APIConnectionError, APIError) as e:
                last_error = e
                logger.warning("llm_error", extra={"model": m, "error": str(e)})
                continue
        raise RuntimeError(f"All models failed. Last error: {last_error}")

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[dict]] = None,
    ) -> AsyncIterator[dict]:
        if not self.configured:
            yield {
                "type": "error",
                "content": "OPENROUTER_API_KEY not configured. Set it in copilot-backend/.env",
            }
            return

        payload = [m.model_dump(exclude_none=True) for m in messages]
        try:
            stream = await self._completion(
                payload, model=model, temperature=temperature, tools=tools, stream=True
            )
        except Exception as e:
            yield {"type": "error", "content": str(e)}
            return

        try:
            async for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                if delta and delta.content:
                    yield {"type": "token", "content": delta.content}
                if delta and getattr(delta, "tool_calls", None):
                    for tc in delta.tool_calls:
                        yield {
                            "type": "tool_call_delta",
                            "index": tc.index,
                            "id": tc.id,
                            "name": tc.function.name if tc.function else None,
                            "arguments": tc.function.arguments if tc.function else None,
                        }
                if choice.finish_reason:
                    yield {"type": "done", "finish_reason": choice.finish_reason}
        except Exception as e:
            yield {"type": "error", "content": str(e)}


def get_llm_client() -> LLMClient:
    from .config import get_settings

    return LLMClient(get_settings())


SYSTEM_PROMPT = """You are **DevOps Copilot**, an AI SRE assistant for a Kubernetes cluster.

## Cluster context
- Namespace: `devops-copilot` (default)
- Workloads: `sample-api` (2 replicas, intentionally buggy), `copilot-backend`, `copilot-frontend`, `postgres`
- Observability: Prometheus + Loki + Grafana in the `monitoring` namespace
- Embedding/RAG: pgvector in `postgres` for runbook retrieval

## Your capabilities
You have access to tools (functions) to:
- `k8s_list_pods`, `k8s_get_pod_logs`, `k8s_describe_pod`, `k8s_list_deployments` — read cluster state
- `prom_query`, `prom_query_range` — run PromQL
- `loki_query` — search logs with LogQL

You also have RAG context retrieved from the runbook (`sample-api.md`).

## When to use tools
- "what's happening" / "is X healthy" → `k8s_list_pods` + `prom_query` for current state
- "why is X slow/erroring/crashing" → `k8s_list_pods` → `k8s_describe_pod` → `k8s_get_pod_logs` → `loki_query` for matching log lines
- "what's the trend" / "over the last X minutes" → `prom_query_range`
- "find error logs" / "search for X" → `loki_query`

## When to use the runbook context
If the user asks about a symptom that's documented in the retrieved runbook, follow the runbook's procedure. Cite the source inline using `[source: filename › section]`.

## Response style
- Concise. Use markdown with fenced code blocks (`promql`, `logql`, `bash`, `yaml`).
- Show the queries you ran (in a code block) and what they returned (a short summary).
- End with a clear **Diagnosis** and **Recommended action** section when the user asked about an issue.
- Never invent metric names or labels. If a query returns no data, say so.
- If a tool call fails, explain what happened and try a different approach (e.g. label selector, different namespace).

## Safety
- This is a read-only agent. You do not have write tools (no scale, no restart, no exec).
- If the user asks you to change the cluster, explain what command they should run and the risk.

## Known failures in `sample-api` (intentional)
1. `/api/users/:id` returns 500 every 7th call (DB timeout simulation)
2. `/api/slow` returns 2-8s responses
3. `/api/error` throws an unhandled exception
4. `/api/leak` grows memory by ~5MB per call
5. `/api/crash` triggers an unhandled promise rejection
6. SIGTERM is not handled (30s graceful-shutdown timeout)

When a user asks about these symptoms, expect to find them in real data.
"""
