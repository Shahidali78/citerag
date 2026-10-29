> Historical record for the original publication. For the protected showcase/live feature, see [current verification](protected-portfolio-verification.md), [security model](security.md) and [deployment gates](deployment.md).

# Local release readiness

## GitHub source preparation

- [x] Existing application preserved; no rebuild from scratch.
- [x] Original datasets, reports, and corpus protected; hashes checked.
- [x] Forty held-out questions with quoted sources/pages and a frozen protocol.
- [x] Twelve-question final set reserved and unexecuted.
- [x] Actual raw real-API reports retained, including retrieval failures.
- [x] MIT license, contribution guidance, CI, issue/PR templates, architecture, screenshots, and deployment guides present.
- [x] Git ignore behavior checked using a local temporary Git metadata directory; .env, .env.local, databases, run history, checkpoints, and .work excluded.
- [x] Source-only Git --no-index diffs reviewed; no commit or push created.
- [x] CI uses isolated fixture/mocked providers and an empty OpenAI key; hosted Actions has not executed.
- [ ] Repository owner approval to initialize/connect a real Git repository and publish the reviewed source.

The project folder was not a Git repository at the start. No tracked-file or commit history is claimed. Temporary review metadata lives only in ignored .work; it has no remote or commits. The publishable candidate inventory is reviewed separately, and actual key values are scanned without printing them. Only the public synthetic example corpus/reports belong in docs.

## Public deployment blockers

- [ ] Authentication/access protection covering BOTH UI and every paid/upload/document API route.
- [ ] Tenant isolation and per-user ownership if moving beyond the single-user assumption.
- [ ] Docker image/container execution and Linux disk ownership validation: Docker Engine is unavailable locally.
- [ ] Durable storage, backup/restore, hosted HTTPS/CORS, cold-start and resource-limit checks on the chosen platform.
- [ ] Review four unpatched upstream Chroma server advisories and the exact-version embedded-only exception before any architecture change; review expires 29 November 2026.
- [ ] Broader development/calibration and a fresh final assessment before claiming experimental reranking preserves recall generally.
- [ ] Explicit owner approval before creating infrastructure or public deployment.

Prepared configuration: Vercel frontend with browser-reachable HTTPS API URL, one Render Docker backend with a durable disk, explicit CORS/hosts, /health, bounded retries/resources, and content-free metrics. CORS and a per-process rate limiter are not authentication or a spending quota. No resources were created, accounts connected, source pushed, or application exposed publicly.

See docs/deployment.md for exact platform steps and docs/security.md for residual risks. Publication of source with honest limitations is distinct from approval to run an unauthenticated public paid endpoint.
