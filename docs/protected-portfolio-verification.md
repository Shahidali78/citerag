# Protected portfolio verification — 2026-10-29

Branch: `feature/protected-portfolio-demo`. This record covers local verification; the pull request supplies the GitHub Actions result for its actual commit. No merge or deployment is authorized.

## Implementation plan and outcome

1. Inspect the existing architecture, Git state, deployment and security gaps. Initial tree was clean; keep all historical evaluation artifacts.
2. Introduce an allowlisted replay showcase and default-deny single-owner live access. Implement the same-origin browser gateway/session and regression tests.
3. Bound real model calls with durable request/token/estimated-cost reservations, output/context caps, and explicit configuration failures.
4. Improve public mode labels, sample questions, private-monitoring notices, documentation and screenshots. Add portfolio copy without posting it.
5. Update CI runtime/action pins and Docker context/secret exclusions; document verified hosting constraints, backup/rollback and unresolved risks.
6. Run local checks, inspect the staged source/history for credentials, push a feature branch and open a PR. Verify remote checks; owner approval is still required before merge or hosting creation/deployment.

## Executed local checks

| Check | Actual result |
| --- | --- |
| Backend pytest | **88 passed** |
| pip check | No broken requirements |
| TypeScript | Passed |
| Next.js production build | Passed; includes dynamic same-origin API gateway |
| Browser showcase suite | **8 passed**, desktop/mobile |
| Browser authenticated fixture suite | **14 passed**, desktop/mobile |
| npm audit | **0 vulnerabilities** |
| Scoped Python audit | 0 unreviewed findings; 4 known unpatched ChromaDB advisories retained |
| Compose configuration | Validates |
| Docker runtime | Engine unavailable; no image build/container execution claimed |
| Public API smoke | Health/session/documents/evaluations serve showcase data; mutation/private-data denial covered by tests |

Local tools: Python 3.12.8 and Node 24.15.0 on Windows. CI uses Python 3.12, application Node 22 and Ubuntu 24.04; passing local checks are not a substitute for the actual PR CI result.

Browser fixtures explicitly clear OPENAI_API_KEY, force the offline provider, bind loopback, use separate ignored databases, and display saved reports without recalculating metrics. They verify authenticated uploads/chat/citations/deletion, replayed public answers, private-data denial, HttpOnly session login/logout, hostile-origin rejection, history races, safe Markdown, monitoring controls and viewport overflow. No paid OpenAI calls were made for this branch. The real API integration was verified previously, not rerun under the new guard here.

The first browser passes exposed an internal-origin comparison bug, an overly broad alert selector and a mobile composer overlap. The origin is now explicitly configured, the selector targets the access region, and sample buttons hide during a conversation. Both complete suites passed afterward; no failures were hidden with forced clicks or provider fallbacks.

## Preservation and security review

Integrity checks cover **44 existing JSON/JSONL/PDF/baseline artifacts**, including original and held-out reports/datasets. All stayed byte-for-byte unchanged. The 12-question final reserve was not executed. Backend .env bytes stayed unchanged; no owner access token was invented. The initial MIT license remains intact.

Code review includes default-deny access, the gateway allowlist/origin/cookie boundary, showcase/private-store separation, budget transactions, error redaction, logs, Docker COPY/ignore rules, CI credentials and exact dependency applicability. The staged source and reachable initial history are scanned for the actual configured key and common OpenAI/GitHub/AWS/private-key/credential-URL patterns. Scanner output contains no secret values. This bounded scan is not a proof against every possible secret.

The final candidate changes are listed in the feature PR. Runtime .env files, uploads, databases, local test logs, caches and review snapshots remain ignored. Screenshots were recaptured only after verifying showcase mode, waiting for sample documents and mode labels to load. Mobile workspace is a full-page capture; evaluation and monitoring captures are viewport crops. Monitoring correctly shows its private-access notice rather than fabricated public activity.

## Review findings and gates

**Blockers for live hosting:** Docker builds/non-root mount ownership/restart persistence, hosted TLS/cookie/origin/body/duration limits, encrypted backup/restore and safe rollback remain unverified. An owner must provide a real high-entropy access secret and current prices. Chroma advisories still require the documented review and expiry gate. Do not reuse the fixed browser test credential, expose multiple replicas, or put the live ledger on ephemeral storage.

**Should improve before stronger production claims:** isolated hostile-PDF processing, edge/global request throttling, crash-safe cross-store ingestion, independent human/unseen-document evaluations and provider-level usage reconciliation. Estimated reservations are not provider-enforced billing caps. CSP permits inline Next.js assets; nonce-based CSP is future work.

**What is working:** explicit server authorization, no-model-call showcase, durable conservative quotas, inspectable citations, preserved reports, offline integration tests and documented limits. The held-out recall tradeoff remains visible and aggressive reranking stays experimental.

Verdict: ready for source PR review after its CI checks; protected deployment still requires the operational gates and owner approval. No public hosting, paid resources, LinkedIn post or PowerPoint work was performed.
