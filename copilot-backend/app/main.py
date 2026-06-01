import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.chat import router as chat_router
from .api.health import router as health_router
from .api.ingest import router as ingest_router
from .config import get_settings
from .embeddings import EmbeddingClient
from .rag import RAGPipeline
from .tools.registry import build_registry
from .vectorstore import VectorStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    app.state.settings = settings
    try:
        app.state.embedder = EmbeddingClient(model_name=settings.embedding_model)
        embedder_ok = True
    except Exception:
        logger.exception("embedder_load_failed_RAG_disabled")
        app.state.embedder = None
        embedder_ok = False

    app.state.vectorstore = VectorStore(
        settings.database_url, dim=settings.embedding_dim
    )

    connected = await app.state.vectorstore.connect()
    if not connected:
        logger.warning(
            "RAG disabled: vector store unreachable at %s", settings.database_url
        )

    if embedder_ok and connected:
        app.state.rag = RAGPipeline(
            app.state.vectorstore,
            app.state.embedder,
            top_k=settings.rag_top_k,
            threshold=settings.rag_similarity_threshold,
        )
    else:
        logger.warning("RAG_disabled embedder=%s db=%s", embedder_ok, connected)
        app.state.rag = None

    if connected and settings.auto_ingest_runbooks:
        runbooks = Path(settings.runbooks_dir)
        if not runbooks.is_absolute():
            runbooks = Path(os.getcwd()) / runbooks
        if runbooks.exists():
            try:
                summary = await app.state.rag.ingest_directory(runbooks)
                logger.info("auto_ingest_complete", extra=summary)
            except Exception as e:
                logger.warning("auto_ingest_failed", extra={"error": str(e)})
        else:
            logger.info("runbooks_dir_skipped", extra={"path": str(runbooks)})

    try:
        app.state.tools, clients = await build_registry(
            prometheus_url=settings.prometheus_url,
            loki_url=settings.loki_url,
            k8s_api_url=settings.k8s_api_url or None,
        )
        app.state._tool_clients = clients
        logger.info("tools_ready")
    except Exception:
        logger.exception("tools_init_failed")
        app.state.tools = None
        app.state._tool_clients = ()

    try:
        yield
    finally:
        for c in getattr(app.state, "_tool_clients", ()):
            try:
                await c.close()
            except Exception:
                pass
        await app.state.vectorstore.close()


app = FastAPI(
    title="DevOps Copilot",
    description="LLM-powered DevOps assistant with RAG + tool-calling agent",
    version="0.3.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(ingest_router)


@app.get("/")
async def root():
    return {
        "service": "copilot-backend",
        "version": "0.3.0",
        "features": ["chat", "rag", "tools", "agent", "health"],
        "docs": "/docs",
    }
