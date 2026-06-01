"""Tests for the markdown-aware chunker used by the RAG pipeline."""
from app.chunker import chunk_markdown


def test_chunker_returns_empty_list_for_empty_input():
    assert chunk_markdown("", source="empty.md") == []


def test_chunker_returns_empty_list_for_whitespace_only():
    assert chunk_markdown("   \n\n   \n", source="blank.md") == []


def test_chunker_keeps_short_single_section_verbatim():
    text = "# Title\n\nThis is a short runbook about restarting pods."
    chunks = chunk_markdown(text, source="test.md")
    assert len(chunks) == 1
    assert chunks[0]["source"] == "test.md"
    assert chunks[0]["section"] == "Title"
    assert "restarting pods" in chunks[0]["content"]


def test_chunker_splits_on_h2_sections():
    text = (
        "# Top\n\n"
        "Intro paragraph.\n\n"
        "## Section A\n\n"
        "Content for A.\n\n"
        "## Section B\n\n"
        "Content for B.\n"
    )
    chunks = chunk_markdown(text, source="multi.md")
    sections = [c["section"] for c in chunks]
    assert "Section A" in sections
    assert "Section B" in sections
    assert any("Content for A" in c["content"] for c in chunks)
    assert any("Content for B" in c["content"] for c in chunks)


def test_chunker_splits_long_section_with_overlap():
    long_paragraph = " ".join(["word"] * 800)  # ~4000 chars
    text = f"# Title\n\n{long_paragraph}"
    chunks = chunk_markdown(text, source="long.md", chunk_size=600, overlap=100)
    assert len(chunks) > 1
    # Each chunk should be at most chunk_size
    for c in chunks:
        assert len(c["content"]) <= 600
    # Chunk indices are sequential
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_chunker_uses_general_section_when_no_heading():
    text = "Just a paragraph with no heading at all.\nAnother line."
    chunks = chunk_markdown(text, source="plain.md")
    assert len(chunks) == 1
    assert chunks[0]["section"] == "general"


def test_chunker_handles_h3_heading():
    # Chunker's primary split is on H2 (`## `). H3 headings are kept
    # inside the parent H2 section's content (as markdown text).
    text = "# Top\n\nIntro.\n\n## H2\n\n### H3\n\nDeep nested content."
    chunks = chunk_markdown(text, source="h3.md")
    h2_chunk = next(c for c in chunks if c["section"] == "H2")
    assert "### H3" in h2_chunk["content"]
    assert "Deep nested content" in h2_chunk["content"]
