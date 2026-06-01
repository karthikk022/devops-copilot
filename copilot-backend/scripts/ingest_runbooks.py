#!/usr/bin/env python3
"""CLI to ingest markdown files into the vector store.

Usage:
    python scripts/ingest_runbooks.py [PATH]

    PATH defaults to ./runbooks
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.embeddings import EmbeddingClient  # noqa: E402
from app.rag import RAGPipeline  # noqa: E402
from app.vectorstore import VectorStore  # noqa: E402


async def main() -> None:
    settings = get_settings()
    target = Path(sys.argv[1] if len(sys.argv) > 1 else settings.runbooks_dir)

    print(f"[ingest] connecting to {settings.database_url}")
    store = VectorStore(settings.database_url, dim=settings.embedding_dim)
    connected = await store.connect()
    if not connected:
        print(
            "[ingest] ERROR: could not connect to vector store. Is Postgres+pgvector running?"
        )
        sys.exit(1)

    print(f"[ingest] loading embedding model {settings.embedding_model}")
    embedder = EmbeddingClient(model_name=settings.embedding_model)
    rag = RAGPipeline(store, embedder)

    print(f"[ingest] scanning {target}")
    summary = await rag.ingest_directory(target)
    print(
        f"[ingest] done: {summary['ingested']} chunks across {len(summary['files'])} files"
    )
    for f in summary["files"]:
        print(f"  - {f['file']}: {f['chunks']} chunks")

    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
