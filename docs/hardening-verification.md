# Hardening verification record

Verified locally on Windows on 29 October 2026 (Europe/Rome). The existing real OpenAI integration and backend/.env key were preserved. CITERAG_DEMO remains false. No GitHub push, public publication, hosted deployment, or paid resource provisioning was performed.

## Actual checks

| Check | Result |
| --- | --- |
| Backend pytest | 58 passed |
| Python dependency compatibility | No broken requirements |
| Frontend TypeScript | Passed |
| Next.js production build | Passed; workspace, evaluations, and monitoring generated |
| Production standalone frontend | Started locally and used for browser checks |
| Desktop/mobile browser checks | 10 distinct checks passed across an initial run and targeted reruns |
| npm audit | Zero vulnerabilities reported |
| Python advisory audit | Four unique unpatched Chroma server findings retained; no unreviewed findings after pip upgrade and scoped applicability review |
| Compose configuration | Validated with docker compose config --quiet |
| Render/Compose/CI YAML | Parsed locally; hosted workflow/deployment not executed |
| Docker Engine | Unavailable; image builds and container startup not run |
| Real PDF and Markdown ingestion after hardening | Passed; temporary verification uploads deleted afterward |
| Real TXT ingestion | Passed through desktop/mobile browser workflows; their own documents deleted |
| Hybrid/local-reranked generation | Passed; actual PDF page-2 code answer with a persisted citation |
| Unsupported question | No citations returned |
| Provider usage and correlation | Real generation tokens present; response request ID matched telemetry |
| CORS, origin/host checks, rate limits, resource limits | API/unit checks passed |
| Retrieval snapshot invalidation and keyword-only candidate scores | Regression tests passed |
| Metrics privacy, retention, missing usage/pricing | Regression tests passed |
| Historical baseline and dataset | Four preserved source files verified byte-for-byte by SHA-256 |
| Corpus | Same original three document IDs, five chunks, and corpus fingerprint after verification cleanup |

The initial browser run passed eight checks. The two upload/chat/evidence workflows reached valid answers and evidence dialogs, then failed because the old chunk-ID selector matched IDs in both the newly added diagnostics and the evidence panel. The selector was scoped to the dialog; only those two workflows were rerun, and both passed. This was an assertion ambiguity, not a hidden application failure. The two dashboard checks were also rechecked after adding citation-support failure flags and run-history switching. No paid calls were needed for screenshots, history, controls, or monitoring checks.

## Real ablations

The retrieval-only study used one shared batch of real query embeddings, the unchanged 16 questions, and the unchanged indexed corpus. Calibration required each question to preserve source recall and expected-evidence token coverage relative to dense. Threshold .2 was selected on the same examples; these are in-sample results.

Fresh answers and structured model judges were run for dense, hybrid, and hybrid plus local reranking. Hybrid alone did not improve precision. Reranked selection improved precision from .4 to .9479 with source recall, MRR, expected-evidence token coverage, and final citation validity at 1.0. Mean selected chunks fell from 5 to 1.5625. Generation input tokens fell from 8657 to 5101, a measured 41.08% reduction.

A dense top-1 control reached perfect filename precision but only .9449 expected-evidence token coverage. This confirms filename-level precision alone is too coarse to establish answer support.

The first reranked report exposed a mixed-refusal regression: a valid cited fact following an opening uncertainty statement was discarded. The validator was fixed and covered by a regression test. Only that question and its judge were rerun. Original raw outputs, the initial comparison, and the corrected report remain separate. After that recheck, correctness, faithfulness, and citation-support judge means were 1.0 for all three configurations, with zero missing scores. These are model judgments, not independent human labels.

The optimized run's lexical F1 is .8149 and faithfulness lexical proxy .8786, lower than the historical .8468/.8960. The comparison retains that tradeoff. Current dense/hybrid/optimized mean measured answer latency is 1.3387/1.2679/1.4366 seconds, excluding the shared embedding batch and optional judging. Historical 1.5719 seconds includes per-question embedding. No statistically proven speed improvement or held-out gain is claimed.

See docs/retrieval-comparison.md, docs/ablation/analysis.json, and the raw reports in docs/ablation/full-study.

## Observability and security

HTTP metrics include server-generated request IDs, UTC timestamps, embedding/retrieval/generation stage durations, available model/token usage, candidate/selected counts, optional configured cost, and status. Raw questions, document contents, and provider error payloads are excluded by default. Existing legacy query_logs were retained and require a separate privacy/retention decision.

Per-process request limits, trusted-host/mutation-origin checks, bounded timeout/retries, safe filenames, PDF/page/character/chunk limits, and streamed body limits are implemented. Unsupported numeric citation IDs remain rejected. Responses and metrics were exercised against the real provider without printing keys.

Pip was upgraded to 26.2.2. Chroma 1.5.9 was the latest available release during verification; the advisory feed listed no patch for four unique server-related advisories. The raw audit is retained. An exact-version, embedded-only applicability exception is documented in docs/security.md and backend/security/advisory-exceptions.json and expires for review on 29 November 2026. No clean Python audit or universally safe dependency is claimed.

## Repository and deployment readiness

MIT license was added as selected by the owner. Contribution guidance, issue/PR templates, credential-free GitHub Actions, Docker health checks, a multi-stage non-root frontend image, a non-root backend image with tested dependency constraints, persistent paths, Render Blueprint, Vercel configuration, screenshots, architecture ADR, deployment instructions, and the professional README are prepared locally.

GitHub Actions has not executed remotely. Docker images, Linux disk ownership, hosted HTTPS/CORS/access protection, provider cold starts, backup/restore, heavy cross-encoder performance, and multi-user production behavior remain unverified. The optional cross-encoder was not downloaded or benchmarked; the tested reranker is the pure-Python heuristic. Authentication and data ownership remain single-user. See docs/deployment.md for exact next steps after approval.
