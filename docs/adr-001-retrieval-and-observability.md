# ADR-001 - Retrieval, evaluation, and observability

Status: implemented locally for the single-user architecture; no public deployment authorized.
Date: 29 October 2026. Maintainer: CiteRAG repository owner.

## Context

The original five-chunk corpus achieved perfect filename recall and 40% precision at K=5 because every query sent all chunks to generation. Citation markers were validated, but broad refusal heuristics could suppress valid supported explanations or partial answers. Request logs lacked correlation, stage usage, and retention; a legacy SQLite audit stored raw questions.

The constraints are to preserve real OpenAI calls, the corpus, questions, baseline reports, document management, and evidence UI. Avoid paid reranking or implicit model downloads. Authentication and data ownership remain single-user.

## Decision

Keep dense retrieval as an explicit baseline. Add pure-Python Okapi BM25 (k1=1.5, b=.75), reciprocal rank fusion (constant=60), and a sentence-coverage/cosine reranker. Reranker scores are heuristic signals, not probabilities. A bounded candidate union is reranked and filtered before final top-K. The original calibration-stage default used hybrid_rerank, 20 candidates, final K=5, and threshold .2, calibrated on the bundled examples. Optional local-only cross-encoder loading uses no remote code and falls back to the lightweight reranker if unavailable. Each model needs its own threshold validation.

BM25 corpus snapshots are cached and invalidated by persisted document IDs, timestamps, chunk counts, and vector count. A configured maximum bounds keyword corpus size; larger corpora fall back explicitly to dense retrieval. This is appropriate for a small local corpus, not a distributed search cluster.

All retained citations refer to selected real chunks. Invalid numeric markers are removed. An unsupported response has no citations; a genuinely supported explanation or partial answer is preserved. Marker validity does not prove claim entailment.

Evaluate retrieval without generation first, then compare fresh generation/judging across the same configurations. Reuse a shared real embedding batch. Retain raw outputs, corpus and dataset hashes, conditions, missing judge counts, and recheck provenance. A dense top-1 control guards against attributing simple evidence truncation to hybrid search.

Store content-free HTTP telemetry in a separate SQLite database: request IDs, UTC timestamps, stages, usage when returned, optional configured cost estimates, counts, and status. Query text storage is now opt-in. Legacy query_logs are preserved, not silently erased. Metrics retention defaults to 30 days. Missing provider usage and prices stay unknown rather than fabricated zeros.

## Options considered

Dense-only is the simplest and remains available, but it sends irrelevant chunks on this corpus. Dense top-1 improves filename precision but drops expected evidence coverage. BM25 plus RRF alone preserves recall but does not improve precision when all five chunks fit in final K. A heavy cross-encoder may improve ranking, but adds model downloads, RAM, latency, and model-specific calibration; it is an optional adapter, not the tested default. Paid hosted reranking was not adopted.

The lightweight reranker plus filtering improved precision in-sample, preserved expected evidence coverage, and reduced measured generation input tokens. Semantic quality checks remained model judgments and lexical F1 fell. No statistically established latency gain or held-out retrieval improvement is claimed.

## Consequences and limits

Retrieval diagnostics and cost attribution are reviewable without logging private content. The original report and corpus remain intact. The pure-Python reranker has no new runtime dependency and fits the local demo.

Keyword scoring is linear in corpus size and snapshot building consumes memory. Calibration uses the evaluation set and needs held-out/adversarial data. An optional cross-encoder has not been downloaded or benchmarked. Single-process rate limits are not global quotas. SQLite/Chroma writes are not a distributed transaction; one replica and a durable volume remain required.

Public deployment still needs access protection covering every API route. Multi-user use needs authentication, tenant isolation, shared durable stores, global rate limits, and background ingestion. Four unpatched upstream Chroma server advisories remain in the raw audit; embedded-only applicability exceptions are documented separately and must be re-reviewed.

## Publication configuration update

The frozen question-level holdout exposed evidence loss from aggressive filtering. The operational default is now hybrid, dense remains recommended, and reranking is experimental. No historical report, threshold or frozen protocol was altered.
