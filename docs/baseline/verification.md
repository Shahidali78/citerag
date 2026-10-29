# Real OpenAI verification

Verified on Windows on 29 October 2026 (Europe/Rome), using Python 3.12.8 and Node.js 24.15.0.

The local backend is configured with `CITERAG_DEMO=false`. The OpenAI key was confirmed present and loaded from `backend/.env` without displaying it. The key was preserved. No environment file was committed. Demo storage and the earlier demo report remain separate; no live failure was masked with a demo fallback.

## Actual checks

| Check | Result |
| --- | --- |
| Real OpenAI embedding API | Passed; 1,536-dimensional vectors persisted |
| Real OpenAI Responses API | Passed with gpt-4.1-mini |
| Markdown upload | sample.md indexed, 2 chunks |
| TXT upload | operations.txt indexed, 1 chunk |
| PDF upload | verification.pdf indexed, 2 chunks on pages 1 and 2 |
| Grounded Q&A | Upload limit and PDF escalation-code questions answered correctly |
| Citation integrity | Stored IDs, document names, pages, and full excerpts matched persisted chunks |
| Unsupported question | Insufficient-evidence response, zero citations |
| Full backend restart | Same 3 document IDs and 5 chunk IDs preserved |
| CORS preflight | Allows http://localhost:3000 |
| Backend pytest | 35 passed |
| Python dependency check | No broken requirements |
| TypeScript typecheck | Passed |
| Next.js production build | Passed |
| Workflow browser tests | 6 passed across desktop and mobile Chromium; real API uploads and chat |
| Dashboard browser tests | 2 passed; saved OpenAI metrics displayed correctly, no horizontal overflow |
| Real evaluations | 16 questions completed with semantic judging; no missing judge values |

The backend runs with `uvicorn app.main:app --reload --port 8000`; the frontend runs with `npm.cmd run dev`. The workspace, evaluation dashboard, and API documentation are available at the requested local URLs.

## Measured real evaluation

Models: `gpt-4.1-mini` and `text-embedding-3-small`. Retrieval depth: K=5. The corpus contains five chunks across sample.md, operations.txt, and verification.pdf. The 16 questions expect sample.md; retrieving both relevant chunks among all five produces Precision@5 of 0.4 even with perfect recall and first-rank retrieval.

| Metric | Actual result |
| --- | --- |
| `answer_lexical_f1` | 0.8468 |
| `source_recall_at_k` | 1.0 |
| `source_precision_at_k` | 0.4 |
| `mrr` | 1.0 |
| `faithfulness_lexical_proxy` | 0.896 |
| `citation_support_lexical_proxy` | 0.9728 |
| `citation_validity` | 1.0 |
| `latency_seconds` | 1.5719 |
| `answer_correctness_judge` | 1.0 |
| `faithfulness_judge` | 1.0 |
| `citation_support_judge` | 1.0 |

Latency is mean question embedding, retrieval, and answer-generation time in seconds; it excludes optional judging. Lexical F1, faithfulness, and evidence-support overlap are proxies. The three judge metrics are model judgments, not proof of factual accuracy. This small, answerable-only benchmark is a smoke test, not a production quality guarantee.

An initial judge response produced no usable scores. Only that judgment was retried, using a strict JSON schema. The live run also exposed a false refusal: a supported explanation of insufficient-evidence behavior contained the same words as a refusal. The detector was narrowed to direct refusals; only that affected question and its judge were rerun. Other measured answers were retained to avoid unnecessary API calls. Retry/recheck metadata is included in the final JSON. No scores were invented or manually substituted.

## Saved evidence

- `backend/evals/results.json`: active real report served by GET /evaluations.
- `docs/openai-evaluation.json`: shareable snapshot of the real report, including raw answers, citations, retrieved chunks, corpus metadata, and recheck history.
- `docs/live-integration.json`: ingestion, stored dimensions, PDF pages, citation checks, restart persistence, and unsupported-question evidence.
- `docs/demo-evaluation.json`: retained historical offline report, labeled mode=demo.
- `backend/evals/refusal-regression.jsonl`: targeted regression example copied from the original dataset.

## Changes made during live verification

`backend/.env` was changed only to disable demo mode while preserving the key. Runtime code now normalizes leading-zero citation markers and avoids the false-refusal bug. Lexical answer F1 excludes citation marker numbers. Evaluations save atomically, retain full audit evidence, validate retrieval depth and nonempty storage, report missing judgments, and support selective judge retries. The optional judge now requests a strict JSON schema.

New integration tooling: `backend/scripts/verify_live.py` and its generated two-page PDF fixture. Browser tests support explicit paid real-mode runs, and a new dashboard suite checks saved metrics. The dashboard identifies the configured models and warns when judge values are missing. Regression tests cover the citation/refusal fixes and ensure complete judgments are not needlessly retried.

## Remaining limits

No billing, permissions, model-access, ingestion, retrieval, citation, CORS, or startup issue remained in the tested paths. The application remains a single-user local project. Automated scores cannot guarantee evidence support or resistance to every document-injection attack. The corpus and benchmark are small; add unanswerable and adversarial questions for stronger quality assessment. PDF OCR, authentication, tenant isolation, and Docker execution are outside this live verification.

See README.md for exact setup, launch, evaluation, and opt-in browser-test commands. Running live integration/evaluation commands again incurs API usage.
