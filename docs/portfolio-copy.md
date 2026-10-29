# Portfolio publication copy

## GitHub title

CiteRAG | Document Q&A with Auditable Evaluations

## Repository description

Document Q&A with recommended dense/BM25 hybrid retrieval, experimental local reranking, page-aware citations, frozen question-level holdout evaluations, and privacy-aware monitoring. Next.js, FastAPI, OpenAI, ChromaDB, and SQLite.

## Five suggested topics

`retrieval-augmented-generation`, `rag-evaluation`, `fastapi`, `nextjs`, `openai`

## AI Engineer resume bullets

- Built a full-stack RAG research workspace with hybrid BM25/vector fusion, local reranking, page-aware evidence citations, and request-level token/latency monitoring.
- Designed a frozen 40-question held-out evaluation and a separate 12-question final reserve, with source-quote verification, gold-evidence metrics, abstention checks, and checkpointed real-API comparisons.
- Identified a retrieval precision/recall tradeoff hidden by a 16-question in-sample benchmark, and added regression tests, privacy controls, Docker packaging, and credential-free CI configuration.

If adding metrics to a resume, state both sides: in-sample reranking reached 94.79% precision at 100% source recall; on the 40-question holdout, it reached 85.42% precision at 84.38% recall. Do not describe either result as a general production guarantee. Test counts and exact limits are in the final verification record.

## LinkedIn announcement draft

I've been working on CiteRAG, a document Q&A app built with Next.js, FastAPI, OpenAI, ChromaDB and SQLite.

The useful part was testing a result that initially looked strong: local reranking reached 94.79% retrieval precision with full recall on 16 calibration questions. On 40 new questions, the same filter reached 85.42% precision but recall fell to 84.38%.

That tradeoff is now visible alongside quoted source evidence, abstention behavior, token usage and raw evaluation reports. The app also includes clickable page citations, hybrid search, monitoring and automated tests.

A separate 12-question final set is still unused. I'm preparing the source for release with the limitations documented, rather than treating an in-sample score as proof of generalization.

## Professional portfolio description

CiteRAG is a full-stack document research application that turns PDF, Markdown and text files into searchable, cited answers. Its FastAPI backend combines OpenAI embeddings, persistent ChromaDB, BM25/vector rank fusion and a configurable local reranker. A responsive Next.js workspace exposes supporting excerpts, page numbers, chunk IDs and retrieval diagnostics.

The project includes content-free request telemetry, bounded ingestion, citation validation, structured quality judging and reproducible evaluations. A 40-question holdout exposed recall loss that the original 16-question calibration benchmark did not reveal. Raw reports and a reserved final set make that limitation reviewable. Docker, deployment files and credential-free CI are prepared locally; public operation still requires access protection, persistent-storage validation and further retrieval development.

## Publication status

These are local drafts. No LinkedIn message, GitHub push, repository publication or deployment was performed. Source publication requires owner approval. An unauthenticated document-upload or paid-model API must not be exposed publicly.
