from pydantic import BaseModel, Field, field_validator
from typing import Literal
from . import config

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=config.FINAL_TOP_K, ge=1, le=12)
    retrieval_mode: Literal['dense', 'hybrid', 'hybrid_rerank'] | None = None
    candidate_count: int | None = Field(default=None, ge=1, le=100)
    relevance_threshold: float | None = Field(default=None, ge=0, le=1)

    @field_validator('question')
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Question must not be blank')
        return value.strip()

class Citation(BaseModel):
    chunk_id: str
    marker: str
    document_id: str
    filename: str
    page: int
    snippet: str
    similarity: float

class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_count: int
    retrieved_sources: list[str] = Field(default_factory=list)
    retrieved_chunks: list[Citation] = Field(default_factory=list)
    raw_answer: str = ''
    diagnostics: list[dict] = Field(default_factory=list)
    retrieval: dict = Field(default_factory=dict)
    telemetry: dict = Field(default_factory=dict)

class DocumentInfo(BaseModel):
    id: str
    filename: str
    chunks: int
    created_at: str

