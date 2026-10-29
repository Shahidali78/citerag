import pytest
from app.chunking import chunk_pages

def test_page_metadata():
    chunks = chunk_pages(["alpha beta", "gamma delta"], size=50, overlap=10)
    assert [c.page for c in chunks] == [1, 2]
    assert [c.index for c in chunks] == [0, 1]

def test_overlap_and_whitespace():
    chunks = chunk_pages(["one   two three four five six seven eight nine"], size=18, overlap=5)
    assert len(chunks) > 1
    assert all("  " not in c.text for c in chunks)

def test_invalid_chunk_size():
    with pytest.raises(ValueError):
        chunk_pages(["abc"], size=10, overlap=10)

