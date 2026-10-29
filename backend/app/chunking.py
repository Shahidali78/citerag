from dataclasses import dataclass

@dataclass(frozen=True)
class Chunk:
    text: str
    page: int
    index: int

def chunk_pages(pages: list[str], size: int = 900, overlap: int = 160) -> list[Chunk]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Require size > overlap >= 0")
    chunks: list[Chunk] = []
    for page_num, page in enumerate(pages, start=1):
        normalized = " ".join(page.split())
        start = 0
        while start < len(normalized):
            end = min(start + size, len(normalized))
            if end < len(normalized):
                boundary = normalized.rfind(" ", start + size // 2, end)
                if boundary > start:
                    end = boundary
            excerpt = normalized[start:end].strip()
            if excerpt:
                chunks.append(Chunk(excerpt, page_num, len(chunks)))
            if end >= len(normalized):
                break
            start = max(start + 1, end - overlap)
    return chunks

