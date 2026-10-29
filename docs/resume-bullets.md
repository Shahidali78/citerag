# Resume bullets

- Built CiteRAG with Next.js, FastAPI, OpenAI Responses/embeddings, persistent ChromaDB, SQLite, and page-aware evidence citations.
- Implemented BM25/vector fusion and evaluated experimental reranking on a frozen 40-question holdout; documented precision increasing from 38.75% to 85.42% alongside source recall falling from 100% to 84.38%.
- Added a replay-only public showcase, server-side single-owner authorization, HttpOnly browser sessions, and atomic daily request/token/estimated-cost reservations before paid model calls.
- Developed backend security regressions and desktop/mobile browser checks with isolated offline fixtures; configured least-privilege CI, dependency audits and non-root Docker packaging.

Use measured results with the qualification that the holdout contains new questions over the same known five-chunk corpus. Do not describe the results as unseen-document generalization or claim that marker validity proves factual correctness.
