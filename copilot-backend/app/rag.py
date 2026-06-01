import logging
from pathlib import Path
from typing import List

from .chunker import chunk_markdown
from .embeddings import EmbeddingClient
from .vectorstore import VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        store: VectorStore,
        embedder: EmbeddingClient,
        top_k: int = 4,
        threshold: float = 0.35,
    ):
        self.store = store
        self.embedder = embedder
        self.top_k = top_k
        self.threshold = threshold

    async def retrieve(self, query: str, top_k: int | None = None) -> List[dict]:
        if not self.store.connected:
            return []
        k = top_k or self.top_k
        emb = self.embedder.embed_one(query)
        results = await self.store.search(emb, top_k=k)
        return [r for r in results if float(r.get("similarity", 0)) >= self.threshold]

    def format_context(self, results: List[dict]) -> str:
        if not results:
            return ""
        blocks: List[str] = ["## Retrieved runbook context\n"]
        for r in results:
            sim = float(r.get("similarity", 0))
            blocks.append(
                f"### Source: `{r['source']}` › {r.get('section', 'general')}  "
                f"(similarity: {sim:.2f})\n"
                f"{r['content']}"
            )
        blocks.append("\n## End of retrieved context\n")
        return "\n\n---\n\n".join(blocks)

    async def ingest_file(self, path: Path) -> int:
        if not path.exists() or path.suffix.lower() not in (".md", ".markdown", ".txt"):
            return 0
        text = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, source=str(path))
        if not chunks:
            return 0
        embeddings = self.embedder.embed([c["content"] for c in chunks])
        return await self.store.upsert(chunks, embeddings)

    async def ingest_directory(self, dir_path: str | Path) -> dict:
        directory = Path(dir_path)
        if not directory.exists():
            logger.warning("runbooks_dir_missing", extra={"path": str(directory)})
            return {"ingested": 0, "files": []}
        results = []
        total = 0
        for f in sorted(directory.glob("**/*")):
            if f.is_file():
                n = await self.ingest_file(f)
                if n > 0:
                    results.append({"file": str(f), "chunks": n})
                    total += n
        return {"ingested": total, "files": results}
