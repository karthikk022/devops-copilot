import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..rag import RAGPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    file: Optional[str] = None
    directory: Optional[str] = None
    content: Optional[str] = None
    source_name: Optional[str] = None


class IngestResponse(BaseModel):
    ingested: int
    files: List[dict]


def get_rag(request: Request) -> RAGPipeline:
    return request.app.state.rag


@router.post("", response_model=IngestResponse)
async def ingest(req: IngestRequest, request: Request, rag: RAGPipeline = Depends(get_rag)):
    if not request.app.state.vectorstore.connected:
        raise HTTPException(status_code=503, detail="vector store not connected")

    from pathlib import Path
    import tempfile

    if req.content is not None and req.source_name is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(req.content)
            tmp_path = Path(f.name)
        try:
            tmp_path = tmp_path.rename(Path(tempfile.gettempdir()) / req.source_name)
            n = await rag.ingest_file(tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return IngestResponse(ingested=n, files=[{"file": req.source_name, "chunks": n}])

    if req.file:
        from pathlib import Path
        n = await rag.ingest_file(Path(req.file))
        return IngestResponse(ingested=n, files=[{"file": req.file, "chunks": n}])

    if req.directory:
        summary = await rag.ingest_directory(req.directory)
        return IngestResponse(**summary)

    raise HTTPException(status_code=400, detail="Provide one of: file | directory | content+source_name")


@router.get("/sources")
async def list_sources(request: Request):
    if not request.app.state.vectorstore.connected:
        return {"connected": False, "sources": [], "count": 0}
    sources = await request.app.state.vectorstore.list_sources()
    count = await request.app.state.vectorstore.count()
    return {"connected": True, "sources": sources, "count": count}
