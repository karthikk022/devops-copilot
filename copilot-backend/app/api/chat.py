import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..llm import LLMClient, SYSTEM_PROMPT, get_llm_client
from ..models import ChatMessage, ChatRequest
from ..rag import RAGPipeline
from ..tools.base import ToolRegistry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_rag(request: Request) -> RAGPipeline:
    return request.app.state.rag


def get_tools(request: Request) -> ToolRegistry:
    return request.app.state.tools


def build_enhanced_system_prompt(base: str, context: str, user_query: str) -> str:
    if not context:
        return base
    return (
        f"{base}\n\n"
        f"## Retrieved runbook context\n"
        f"If the user's question matches the runbook context below, use it. "
        f"Cite the source inline as `[source: filename › section]`.\n\n"
        f"{context}\n\n"
        f"## Current user question\n"
        f'"{user_query}"'
    )


@router.post("")
async def chat(
    req: ChatRequest,
    request: Request,
    llm: LLMClient = Depends(get_llm_client),
    rag: RAGPipeline = Depends(get_rag),
    tools: ToolRegistry = Depends(get_tools),
) -> StreamingResponse:
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    settings = request.app.state.settings
    user_query = next(
        (m.content for m in reversed(req.messages) if m.role == "user"),
        "",
    )

    retrieved: list[dict] = []
    if user_query and rag and request.app.state.vectorstore.connected:
        try:
            retrieved = await rag.retrieve(user_query)
        except Exception as e:
            logger.warning("rag_retrieve_failed", extra={"error": str(e)})
    context_str = rag.format_context(retrieved) if retrieved else ""
    enhanced_system = build_enhanced_system_prompt(
        SYSTEM_PROMPT, context_str, user_query
    )

    working: list[ChatMessage] = list(req.messages)
    if not working or working[0].role != "system":
        working.insert(0, ChatMessage(role="system", content=enhanced_system))
    else:
        working[0] = ChatMessage(role="system", content=enhanced_system)

    async def event_source() -> AsyncIterator[bytes]:
        try:
            if retrieved:
                meta = {
                    "type": "rag_citation",
                    "results": [
                        {
                            "source": r["source"],
                            "section": r.get("section"),
                            "similarity": float(r.get("similarity", 0)),
                        }
                        for r in retrieved
                    ],
                }
                yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n".encode(
                    "utf-8"
                )

            tool_schemas = tools.schemas() if tools else []
            max_iter = settings.agent_max_iterations

            for iteration in range(max_iter):
                accumulated_calls: dict[int, dict] = {}
                finish_reason = None

                async for chunk in llm.stream_chat(
                    working,
                    model=req.model,
                    temperature=req.temperature,
                    tools=tool_schemas or None,
                ):
                    if chunk["type"] == "tool_call_delta":
                        idx = chunk.get("index", 0) or 0
                        slot = accumulated_calls.setdefault(
                            idx, {"id": None, "name": None, "arguments": ""}
                        )
                        if chunk.get("id"):
                            slot["id"] = chunk["id"]
                        if chunk.get("name"):
                            slot["name"] = chunk["name"]
                        if chunk.get("arguments"):
                            slot["arguments"] += chunk["arguments"]
                    elif chunk["type"] == "token":
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode(
                            "utf-8"
                        )
                    elif chunk["type"] == "done":
                        finish_reason = chunk.get("finish_reason")
                    elif chunk["type"] == "error":
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode(
                            "utf-8"
                        )
                        return

                if finish_reason != "tool_calls" or not accumulated_calls:
                    yield f"data: {json.dumps({'type': 'done', 'finish_reason': finish_reason}, ensure_ascii=False)}\n\n".encode(
                        "utf-8"
                    )
                    return

                ordered_calls = [
                    accumulated_calls[i] for i in sorted(accumulated_calls.keys())
                ]
                working.append(
                    ChatMessage(
                        role="assistant",
                        content="",
                    ).model_dump()  # type: ignore[arg-type]
                ) if False else None
                tool_calls_payload = []
                for c in ordered_calls:
                    try:
                        args = json.loads(c["arguments"]) if c["arguments"] else {}
                    except Exception:
                        args = {"_raw": c["arguments"]}
                    tool_calls_payload.append(
                        {
                            "id": c["id"],
                            "type": "function",
                            "function": {
                                "name": c["name"],
                                "arguments": c["arguments"] or "{}",
                            },
                        }
                    )

                assistant_tool_msg = ChatMessage(
                    role="assistant",
                    content="",
                )
                working[-1] = assistant_tool_msg

                tool_results: list[ChatMessage] = []
                for c, payload in zip(ordered_calls, tool_calls_payload):
                    args = (
                        json.loads(payload["function"]["arguments"])
                        if payload["function"]["arguments"]
                        else {}
                    )
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool_name': c['name'], 'tool_args': args, 'tool_call_id': c['id']}, ensure_ascii=False)}\n\n".encode(
                        "utf-8"
                    )
                    if tools is None:
                        result = (
                            f"Tool '{c['name']}' is unavailable in this environment. "
                            "The Kubernetes/Prometheus/Loki tools were not initialized "
                            "at startup (no cluster or observability stack reachable). "
                            "Provide a direct answer based on your knowledge instead."
                        )
                    else:
                        try:
                            result = await tools.call(c["name"], args)
                        except Exception as e:
                            logger.exception(
                                "tool_call_failed", extra={"tool": c["name"]}
                            )
                            result = f"Tool '{c['name']}' failed: {e}"
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': c['name'], 'content': result[:4000], 'tool_call_id': c['id']}, ensure_ascii=False)}\n\n".encode(
                        "utf-8"
                    )
                    tool_results.append(
                        ChatMessage(
                            role="tool",
                            content=result,
                            name=c["name"],
                            tool_call_id=c["id"],
                        )
                    )

                if (
                    not isinstance(working[-1], ChatMessage)
                    or working[-1].role != "assistant"
                ):
                    working.append(ChatMessage(role="assistant", content=""))
                working.append(ChatMessage(role="user", content=""))
                working.extend(tool_results)

        except Exception as e:
            logger.exception("chat_stream_error")
            err = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {err}\n\n".encode("utf-8")

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
