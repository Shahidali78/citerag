"""Local BM25 + RRF retrieval with transparent, non-probabilistic ranking scores."""
from collections import Counter
from dataclasses import dataclass, asdict
from functools import lru_cache
import math
import re
from . import config
from .store import collection, list_documents

STOP = set('a an the is are was were what which how does do can to in of and or for with from my your it its this that be on by at as'.split())

def terms(text: str) -> list[str]:
    return [word for word in re.findall(r'[a-z0-9]+', text.lower()) if word not in STOP]

@dataclass(frozen=True)
class RetrievalOptions:
    mode: str = 'dense'
    candidates: int = 20
    top_k: int = 5
    threshold: float = 0.25

    def __post_init__(self):
        if self.mode not in {'dense', 'hybrid', 'hybrid_rerank'} or not 1 <= self.top_k <= 12 or not 1 <= self.candidates <= 100 or not 0 <= self.threshold <= 1:
            raise ValueError('Invalid retrieval options')

    @classmethod
    def defaults(cls, top_k: int | None = None):
        return cls(config.RETRIEVAL_MODE, config.CANDIDATE_COUNT, top_k or config.FINAL_TOP_K, config.RELEVANCE_THRESHOLD)

@dataclass
class Candidate:
    chunk_id: str
    text: str
    metadata: dict
    vector_similarity: float | None = None
    keyword_score: float = 0.0
    rrf_score: float | None = None
    fusion_rank: int | None = None
    rerank_score: float | None = None
    selected: bool = False

    def diagnostic(self):
        return {key: value for key, value in asdict(self).items() if key not in {'text', 'metadata'}} | {'filename': self.metadata['filename'], 'page': self.metadata['page']}

class BM25:
    """Okapi BM25, k1=1.5, b=.75, Robertson non-negative IDF."""
    def __init__(self, texts: list[str]):
        self.documents = [Counter(terms(text)) for text in texts]
        self.lengths = [sum(doc.values()) for doc in self.documents]
        self.average = sum(self.lengths) / max(1, len(texts))
        self.df = Counter(word for doc in self.documents for word in doc)
        self.count = len(texts)

    def idf(self, word: str) -> float:
        frequency = self.df.get(word, 0)
        return math.log(1 + (self.count - frequency + .5) / (frequency + .5))

    def scores(self, question: str) -> list[float]:
        query = set(terms(question))
        return [sum(self.idf(word) * doc[word] * 2.5 / (doc[word] + 1.5 * (.25 + .75 * length / (self.average or 1))) for word in query if doc[word]) for doc, length in zip(self.documents, self.lengths)]

def reciprocal_rank_fusion(rankings: list[list[str]], constant: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(dict.fromkeys(ranking), 1):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (constant + rank)
    return scores

@lru_cache(maxsize=8)
def _snapshot(path: str, name: str, revision: tuple, count: int):
    # SQLite document IDs/timestamps invalidate this cache across processes too.
    stored = collection().get(include=['documents', 'metadatas'])
    order = sorted(range(len(stored['ids'])), key=lambda i: stored['ids'][i])
    rows = [(stored['ids'][i], stored['documents'][i], stored['metadatas'][i]) for i in order]
    return rows, BM25([row[1] for row in rows])

@lru_cache(maxsize=2)
def _cross_encoder(model: str):
    if not model:
        return None
    try:
        from sentence_transformers import CrossEncoder
        # Never download models implicitly or call a paid reranking service.
        return CrossEncoder(model, device='cpu', local_files_only=True, trust_remote_code=False)
    except (ImportError, OSError, ValueError, TypeError, RuntimeError):
        return None

def lightweight_score(question: str, candidate: Candidate, index: BM25) -> float:
    query = set(terms(question))
    denominator = sum(index.idf(word) for word in query) or 1
    # Sentence coverage is less length-biased than raw BM25 for long chunks.
    coverage = max((sum(index.idf(word) for word in query & set(terms(sentence))) / denominator for sentence in re.split(r'(?<=[.!?])\s+', candidate.text)), default=0)
    return .65 * coverage + .35 * max(0, candidate.vector_similarity or 0)

def retrieve(question: str, vector: list[float], options: RetrievalOptions):
    col = collection()
    count = col.count()
    if not count:
        return [], [], {'reranker_used': None, 'fallback': None, 'options': asdict(options)}
    pool = min(count, options.top_k if options.mode == 'dense' else max(options.top_k, options.candidates))
    raw = col.query(query_embeddings=[vector], n_results=pool, include=['documents', 'metadatas', 'distances'])
    candidates = {chunk_id: Candidate(chunk_id, text, metadata, 1-float(distance)) for chunk_id, text, metadata, distance in zip(raw['ids'][0], raw['documents'][0], raw['metadatas'][0], raw['distances'][0])}
    dense_order = list(candidates)
    fallback = None
    reranker_used = None
    if options.mode != 'dense' and count <= config.MAX_KEYWORD_CHUNKS:
        revision = tuple((d['id'], d['chunks'], d['created_at']) for d in list_documents())
        rows, index = _snapshot(config.CHROMA_PATH, col.name, revision, count)
        scores = index.scores(question)
        keyword_order = sorted(range(len(rows)), key=lambda i: (-scores[i], rows[i][0]))
        keyword_order = [i for i in keyword_order if scores[i] > 0][:pool]
        all_rows = {row[0]: (row, scores[i]) for i, row in enumerate(rows)}
        for i in keyword_order:
            chunk_id, text, metadata = rows[i]
            candidates.setdefault(chunk_id, Candidate(chunk_id, text, metadata))
        # Obtain original cosine scores for keyword-only candidates from persisted vectors.
        missing = [chunk_id for chunk_id, c in candidates.items() if c.vector_similarity is None]
        if missing:
            embeddings = col.get(ids=missing, include=['embeddings'])
            norm = math.sqrt(sum(v*v for v in vector)) or 1
            for chunk_id, embedding in zip(embeddings['ids'], embeddings['embeddings']):
                similarity = sum(a*b for a,b in zip(vector, embedding)) / (norm * (math.sqrt(sum(float(v)*float(v) for v in embedding)) or 1))
                candidates[chunk_id].vector_similarity = float(similarity)
        for chunk_id, candidate in candidates.items():
            candidate.keyword_score = all_rows.get(chunk_id, (None, 0))[1]
        fusion = reciprocal_rank_fusion([dense_order, [rows[i][0] for i in keyword_order]])
        order = sorted(candidates, key=lambda key: (-fusion[key], key))
        for rank, chunk_id in enumerate(order, 1):
            candidates[chunk_id].rrf_score = fusion[chunk_id]
            candidates[chunk_id].fusion_rank = rank
        # A candidate budget limits the union as well as each input ranking.
        order = order[:max(options.top_k, options.candidates)]
        if options.mode == 'hybrid_rerank':
            reranker_used = 'lightweight'
            model = _cross_encoder(config.RERANKER_MODEL) if config.RERANKER == 'cross_encoder' else None
            if config.RERANKER == 'cross_encoder' and model is None:
                fallback = 'Local cross-encoder unavailable; using lightweight reranker'
            if model is not None:
                try:
                    values = model.predict([(question, candidates[key].text) for key in order])
                    if len(values) != len(order) or not all(math.isfinite(float(value)) for value in values):
                        raise ValueError('Invalid reranker scores')
                    for key, value in zip(order, values):
                        candidates[key].rerank_score = 1 / (1 + math.exp(-max(-40, min(40, float(value)))))
                    reranker_used = 'cross_encoder'
                except Exception:
                    fallback = 'Local cross-encoder failed; using lightweight reranker'
            if reranker_used == 'lightweight':
                for key in order:
                    candidates[key].rerank_score = lightweight_score(question, candidates[key], index)
            order.sort(key=lambda key: (-candidates[key].rerank_score, candidates[key].fusion_rank))
            order = [key for key in order if candidates[key].rerank_score >= options.threshold]
    else:
        order = dense_order
        if options.mode != 'dense':
            fallback = 'Keyword corpus exceeds configured memory bound; using dense retrieval'
    selected = [candidates[key] for key in order[:options.top_k]]
    for candidate in selected:
        candidate.selected = True
    return selected, list(candidates.values()), {'reranker_used': reranker_used, 'fallback': fallback, 'options': asdict(options)}
