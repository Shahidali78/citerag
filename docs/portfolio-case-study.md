# CiteRAG engineering case study

## Project overview

CiteRAG is a document research workspace for PDF, TXT and Markdown. It returns answers with inspectable source excerpts, filenames, one-based pages and persistent chunk IDs. The portfolio includes a public showcase that replays saved sample answers without new model calls, and a protected single-owner live workspace. Next.js provides the UI and same-origin API gateway; FastAPI owns retrieval, storage, authorization and model access.

## Engineering challenge

An LLM can produce fluent claims that are missing from the supplied documents. Retrieval narrows the available evidence; citations let a reader check the result. Neither technique proves truth. In particular, a valid citation identifier can point to an excerpt that does not support the attached claim. CiteRAG separates marker validity, evidence coverage and semantic support rather than treating one score as a reliability guarantee.

## Architecture

Uploads pass extension, filename, body, extraction, page and chunk limits. PDF text keeps page boundaries. Text is split into 900-character chunks with 160-character overlap within a page. OpenAI text-embedding-3-small generates vectors, stored through embedded Chroma PersistentClient. SQLite stores document metadata and content-free telemetry; a separate SQLite ledger serializes daily usage reservations.

Dense search ranks cosine neighbors. Hybrid search combines dense and Okapi BM25 rankings through reciprocal rank fusion with constant 60. The optional lightweight reranker uses sentence coverage and vector similarity, then filters by a threshold. Hybrid is the operational default; dense is also recommended. Aggressive reranking is experimental.

Selected chunks become JSON-encoded untrusted evidence for the OpenAI Responses API. Citation validation maps numbered markers to actual selected chunks and removes nonexistent identifiers. The evidence panel shows supporting excerpts. Prompt injection remains a model limitation; treating retrieved instructions as data is a mitigation, not a proof of resistance.

In showcase mode, the server bypasses ingestion, runtime databases and all model clients. It serves only allowlisted bundled reports and exact saved questions/answers. Reports retain their original real-API labels, metrics and shortcomings; request telemetry identifies replay rather than implying a new inference.

## Technical decisions

- **Embedded Chroma:** simple persistent vector storage for a small corpus, without a separately exposed Chroma server. This limits scaling and retains four upstream dependency advisories under a scoped review.
- **SQLite:** inspectable local state and atomic quota reservations across concurrent requests. One API process/replica and one durable disk remain the deployment model. Document metadata and vectors are not a cross-store transaction.
- **Hybrid as default:** retains the observed evidence recall while improving ordering on this small dataset. This does not establish generalization to unseen corpora.
- **Local reranking:** transparent and inexpensive to run, but its relevance filter can remove essential evidence. A local-only cross-encoder adapter exists; it was not provisioned or benchmarked.
- **OpenAI:** real embeddings and Responses integration, isolated to the backend. A wrapper caps output, bounds context and reserves estimated usage before every paid SDK call. Live calls require owner-supplied pricing; showcase requires no key.
- **Single-owner authentication:** bearer verification on the API, with a one-hour HttpOnly/SameSite=Strict browser cookie through the Next.js gateway. The gateway validates mutation origins and keeps the token out of browser JavaScript. This avoids adding unsupported multi-user claims.

## Evaluation findings

The original 16 questions were also used to calibrate the reranking threshold. On that in-sample benchmark, reranking reached 94.79% filename precision with 100% source recall; this was not an independent quality improvement claim.

The later frozen question-level assessment used 40 new questions over the same known five-chunk corpus: 32 answerable and eight unanswerable. A separate 12-question reserve remains unexecuted.

| Method | Source recall | Filename precision | Lexical F1 | Correctness judge |
| --- | ---: | ---: | ---: | ---: |
| Dense | 100% | 38.75% | 68.85% | 100% |
| Hybrid | 100% | 38.75% | 70.83% | 100% |
| Hybrid + reranking | 84.38% | 85.42% | 60.36% | 87.50% |

Reranking lost complete or partial evidence in six answerable cases and fully refused four. Raw citation-marker validity remained 100%, while answerable citation coverage fell to 87.5%. Higher precision did not compensate for missing evidence. Its lower generation-token total partly reflected missed context and refusals, not quality-neutral efficiency.

Gold quotes identify acceptable overlapping chunk alternatives. Metrics distinguish filename relevance, gold-evidence relevance, lexical overlap, strict abstention and optional semantic judging. The corpus is tiny and known; these are new-question holdouts, not unseen-document/domain or externally blind evaluations. No held-out failure was regenerated or manually corrected. See [full results](heldout-results.md) and immutable JSON under `docs/heldout/v1`.

## Reliability and security

Tests cover uploads, retrieval, citation cleanup, evaluation integrity, unauthorized access, showcase isolation, atomic quotas, output limits and browser session behavior. CI requires no OpenAI credentials. Monitoring stores request IDs, timings and token usage rather than questions or excerpts. Live upload and chat requests consume persistent daily allowances; failed provider calls retain conservative reservations because billing may be unknown.

Public showcase routes cannot upload/delete documents, access private monitoring or instantiate a provider. Live access fails closed without a sufficiently long owner token. Costs remain estimates dependent on configured rates; this is not a provider-enforced billing cap. The owner must use HTTPS, strong secret storage and a restricted OpenAI project. PDF parsing is bounded but not sandboxed, in-memory request throttling is not distributed, and hosted storage/restore checks still require deployment validation.

## Lessons and future work

The held-out assessment exposed a recall cost hidden by a calibration benchmark. Evaluate retrieval independently from generation, inspect support rather than only marker validity, and freeze conditions before scoring. Saved outputs and honest denominators make a modest experiment more useful than a large unsupported headline.

Future work includes independently reviewed unseen-document data, stronger abstention policy, isolated PDF parsing, a development-only retrieval calibration set, distributed limits if scaling becomes necessary, and verified container/hosted backup recovery. No new benchmark or final reserve was run for this security feature branch.
