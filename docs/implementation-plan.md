# Implementation plan

Preserve the original corpus, dataset, reports, and credentials. Add independent retrieval and telemetry modules without replacing ingestion or the UI.

1. Keep dense top-K as the baseline. Add local BM25, reciprocal rank fusion, a lightweight local reranker, optional local-only cross-encoder loading, and explicit score diagnostics.
2. Calibrate filtering on the existing labeled sample set without claiming held-out gains. Include a dense top-1 control to expose gains caused only by passing fewer chunks. Preserve expected-evidence coverage as well as source recall.
3. Run retrieval-only ablations with one shared batch of real query embeddings. Run comparable fresh answer evaluations with optional judges, saving immutable history and separating embedding/generation timings.
4. Add request IDs, stage timings, usage, optional configured pricing, content-free metrics, retention, rate limiting, bounded ingestion, and a monitoring API.
5. Extend the evaluation UI with configuration/history selectors, comparisons, failure analysis, and monitoring. Preserve document management, Markdown safety, and citations.
6. Harden Docker, add health checks and CI without credentials, add the selected MIT license and contribution guidance, and document deployment without publishing.
7. Run backend, frontend, browser, and targeted live checks; preserve raw reports and record limits honestly.
