import json
import logging
from typing import List, Optional

import asyncpg

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, dsn: str, dim: int = 384):
        self.dsn = dsn
        self.dim = dim
        self.pool: Optional[asyncpg.Pool] = None
        self.connected = False

    async def connect(self) -> bool:
        if self.connected:
            return True
        try:
            self.pool = await asyncpg.create_pool(
                self.dsn, min_size=1, max_size=5, command_timeout=10
            )
            await self._init_schema()
            self.connected = True
            logger.info("vector_store_connected")
            return True
        except Exception as e:
            logger.warning("vector_store_connect_failed", extra={"error": str(e)})
            self.pool = None
            self.connected = False
            return False

    async def _init_schema(self) -> None:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    section TEXT,
                    chunk_index INT NOT NULL DEFAULT 0,
                    content TEXT NOT NULL,
                    embedding vector({self.dim}) NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS documents_embedding_hnsw
                ON documents USING hnsw (embedding vector_cosine_ops);
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS documents_source_idx
                ON documents (source);
                """
            )

    async def upsert(
        self,
        chunks: List[dict],
        embeddings: List[List[float]],
    ) -> int:
        assert self.pool is not None
        if not chunks:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must be the same length")

        rows = [
            (
                c["source"],
                c.get("section", "general"),
                int(c.get("chunk_index", i)),
                c["content"],
                emb,
                json.dumps(c.get("metadata", {})),
            )
            for i, (c, emb) in enumerate(zip(chunks, embeddings))
        ]

        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM documents WHERE source = $1",
                rows[0][0],
            )
            await conn.executemany(
                """
                INSERT INTO documents
                  (source, section, chunk_index, content, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5::vector, $6::jsonb)
                """,
                rows,
            )
        logger.info("vector_store_upserted", extra={"source": rows[0][0], "chunks": len(rows)})
        return len(rows)

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 4,
    ) -> List[dict]:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT source, section, content,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM documents
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                query_embedding,
                top_k,
            )
        return [dict(r) for r in rows]

    async def count(self, source: Optional[str] = None) -> int:
        if not self.pool:
            return 0
        async with self.pool.acquire() as conn:
            if source:
                return await conn.fetchval("SELECT COUNT(*) FROM documents WHERE source = $1", source)
            return await conn.fetchval("SELECT COUNT(*) FROM documents")

    async def list_sources(self) -> List[str]:
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT source FROM documents ORDER BY source")
        return [r["source"] for r in rows]

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.connected = False
