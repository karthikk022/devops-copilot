from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=50)
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    stream: bool = True


class ChatChunk(BaseModel):
    type: Literal["token", "done", "error", "tool_call"]
    content: str = ""
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    finish_reason: Optional[str] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    llm_configured: bool
    model: str
    fallback_models: List[str]
