"""Tests for the RAG context formatter and pipeline structure."""

from app.rag import RAGPipeline


class FakeVectorStore:
    """Stand-in for VectorStore that records upserts/searches but never connects."""

    def __init__(self):
        self.connected = False
        self.upserts = []
        self.searches = []

    async def connect(self):
        return False

    async def search(self, embedding, top_k=4):
        self.searches.append((embedding, top_k))
        return []

    async def upsert(self, chunks, embeddings):
        self.upserts.append((chunks, embeddings))
        return len(chunks)


class FakeEmbedder:
    """Stand-in for EmbeddingClient that returns the input as a fake embedding."""

    def __init__(self, dim=4):
        self.dim = dim

    def embed(self, texts):
        return [[0.1] * self.dim for _ in texts]

    def embed_one(self, text):
        return [0.1] * self.dim


def test_format_context_returns_empty_string_for_no_results():
    rag = RAGPipeline(
        store=FakeVectorStore(),
        embedder=FakeEmbedder(),
    )
    assert rag.format_context([]) == ""


def test_format_context_includes_source_section_and_similarity():
    rag = RAGPipeline(
        store=FakeVectorStore(),
        embedder=FakeEmbedder(),
    )
    results = [
        {
            "source": "runbooks/pods.md",
            "section": "CrashLoopBackOff",
            "content": "Restart the deployment.",
            "similarity": 0.87,
        }
    ]
    out = rag.format_context(results)
    assert "runbooks/pods.md" in out
    assert "CrashLoopBackOff" in out
    assert "0.87" in out
    assert "Restart the deployment." in out
    assert "Retrieved runbook context" in out
    assert "End of retrieved context" in out


def test_format_context_joins_multiple_results_with_separator():
    rag = RAGPipeline(
        store=FakeVectorStore(),
        embedder=FakeEmbedder(),
    )
    results = [
        {"source": "a.md", "section": "S1", "content": "first", "similarity": 0.9},
        {"source": "b.md", "section": "S2", "content": "second", "similarity": 0.8},
    ]
    out = rag.format_context(results)
    assert "first" in out and "second" in out
    # The separator between blocks
    assert "---" in out


def test_retrieve_returns_empty_when_vectorstore_not_connected():
    rag = RAGPipeline(
        store=FakeVectorStore(),  # connected=False
        embedder=FakeEmbedder(),
    )
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(rag.retrieve("anything"))
    assert result == []
