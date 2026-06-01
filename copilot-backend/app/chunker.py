import re
from typing import Dict, List


def chunk_markdown(
    text: str,
    source: str,
    chunk_size: int = 600,
    overlap: int = 100,
) -> List[Dict]:
    """Markdown-aware chunker.

    Splits on H2 sections first, then breaks long sections into overlapping
    paragraph-aware windows. Each chunk carries metadata for citation.
    """
    chunks: List[Dict] = []
    sections = re.split(r"\n(?=## )", text)

    for raw_section in sections:
        section = raw_section.strip()
        if not section:
            continue

        lines = section.split("\n")
        first = lines[0]
        if first.startswith("#"):
            section_title = first.lstrip("#").strip() or "general"
            body = "\n".join(lines[1:]).strip()
        else:
            section_title = "general"
            body = section

        if not body:
            continue

        if len(body) <= chunk_size:
            chunks.append(
                {
                    "source": source,
                    "section": section_title,
                    "chunk_index": len(chunks),
                    "content": body,
                }
            )
        else:
            step = max(chunk_size - overlap, 1)
            for i in range(0, len(body), step):
                piece = body[i : i + chunk_size].strip()
                if not piece:
                    continue
                chunks.append(
                    {
                        "source": source,
                        "section": section_title,
                        "chunk_index": len(chunks),
                        "content": piece,
                    }
                )
                if i + chunk_size >= len(body):
                    break

    return chunks
