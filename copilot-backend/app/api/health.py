from fastapi import APIRouter, Depends, Request

from .. import __version__
from ..config import Settings, get_settings
from ..llm import LLMClient, get_llm_client
from ..models import HealthResponse

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health(
    request: Request,
    settings: Settings = Depends(get_settings),
    llm: LLMClient = Depends(get_llm_client),
) -> HealthResponse:
    rag_connected = bool(
        getattr(request.app.state, "vectorstore", None)
        and request.app.state.vectorstore.connected
    )
    if not llm.configured:
        status = "degraded"
    elif not rag_connected:
        status = "degraded"
    else:
        status = "ok"

    return HealthResponse(
        status=status,
        version=__version__,
        llm_configured=llm.configured,
        model=settings.llm_model,
        fallback_models=settings.fallback_models,
    )
