# Security model and review

Updated for the protected portfolio feature branch. Tests are evidence of specific behavior, not a declaration that the system is fully secure.

## Trust boundaries and access policy

A fresh process defaults to `CITERAG_ACCESS_MODE=showcase`. It can read only allowlisted bundled public reports and replay their exact questions/answers. It never instantiates a provider or reads runtime documents/monitoring/history. Uploads, deletion, arbitrary questions and private monitoring are denied. The bundled reports are deliberately public synthetic artifacts.

Live mode requires an owner-supplied `CITERAG_ACCESS_TOKEN` of at least 32 characters. Without one, data routes fail closed with 503. Wrong/missing credentials receive 401. Authentication covers document reads, upload/deletion, chat, monitoring, runtime evaluation history, Swagger/OpenAPI and future unmatched routes by default. Health/session status and CORS preflight disclose only minimal configuration/session status. There is no HTTP evaluation-launch endpoint; CLI execution requires access to the backend host and its environment.

The Next.js gateway validates an exact `CITERAG_FRONTEND_ORIGIN` for mutations. Login verifies the user-supplied token against the backend, then sets a one-hour HttpOnly, SameSite=Strict cookie. Secure is required on production HTTPS; `CITERAG_LOCAL_HTTP=true` is an explicit loopback-only testing override. The gateway reads the cookie server-side and forwards a bearer header. It never trusts browser-provided Authorization/Host or proxies arbitrary URLs. Token storage is the host environment, not source or browser localStorage. Rotating the backend token revokes existing sessions. A fixed token in isolated tests is not a deployment credential.

## Control review

| Area | Implemented control and remaining limit |
| --- | --- |
| API key | Backend environment only; no browser/public variable, logs or image copy. Existing .env preserved. |
| Authentication/authorization | Constant-time owner-token comparison, default-deny live policy and private monitoring/documents/reports. Single owner, not tenants or individual audit identities. |
| Upload validation | PDF/TXT/MD extension, normalized basename, UTF-8, 20 MB declared/streamed bound, PDF page limit, extraction/character/chunk limits and corpus capacity check. |
| PDF safety | Parsing runs off the event loop and has resource bounds; no malware scanning or isolated subprocess time/memory sandbox. Hostile PDF parsing remains a deployment risk. |
| Input/context | Question <=4000 chars, K<=12, candidates<=100; generation context capped before the paid call. No silent truncation of evidence. |
| Prompt injection | Retrieved text is JSON-encoded untrusted evidence under fixed instructions. This does not guarantee model compliance. |
| Citations | Numeric IDs checked against selected chunks; excerpts/page/IDs inspectable. Marker validity is not entailment. |
| CORS/hosts | Explicit backend origins/hosts, mutation-origin checks, browser gateway origin checks. CORS is not authorization. |
| Rate/usage limits | Per-process sliding window; SQLite atomic daily request/token/estimated-USD reservations shared across concurrent calls and restarts. One worker/replica and edge throttling remain required. |
| Timeouts/retries | Bounded SDK timeout/retry count; gateway timeout; reservations include the retry ceiling. Multi-batch ingestion can outlast one browser request. |
| Logging/errors | Generic provider errors, request IDs and allowlisted telemetry. No questions/excerpts/credentials in telemetry. Proxy/login failures do not return provider exception text. |
| Browser/session | HttpOnly cookie, SameSite=Strict, configured mutation origin, no-store API responses, frame denial, no-referrer and basic CSP. CSP permits inline Next.js scripts/styles; nonce-based CSP is future hardening. |
| Dependencies | npm and scoped Python audits remain enabled; four Chroma issues remain unresolved. |
| Docker | Non-root users, explicit COPY paths, secret/cache exclusions, loopback Compose ports and persistent volume. Engine unavailable; runtime ownership/restart behavior unverified. |
| Environment | Examples only in Git. Missing owner token or model prices disables live access/paid calls rather than inventing credentials. |
| Retention | Metrics default 30 days; quota ledger 31 days. Documents remain until owner deletion. Legacy query_logs may hold older private text; review/delete under the owner's retention policy. |
| Public exposure | Showcase is the only anonymous app mode. Do not expose a live Chroma server or reuse fixture credentials. Hosted HTTPS, storage and recovery remain approval-gated. |

## Cost reservations

The owner configures positive model rates. A UTF-8-byte input overbound, framing allowance, configured maximum output and retry ceiling reserve tokens and estimated USD before every real SDK call, including CLI evaluations. Reservations are deliberately not refunded for errors/unknown usage. This can reject requests earlier than actual spending would require. It is not an invoice reconciliation system or provider-enforced monetary ceiling: rates/model changes, provider accounting and external use of the same key are outside this ledger. Use a separate restricted provider project and observe its usage.

Daily HTTP request quotas count chat/upload attempts even if validation or generation later fails. Quotas reset at UTC midnight and persist on the same durable volume as the corpus. Do not use multiple backend replicas or reset/delete the ledger to bypass limits. Never put the backend ledger on an ephemeral live filesystem.

## ChromaDB applicability and upgrade review

Installed and latest package-index release at this review: chromadb **1.5.9**. The fresh advisory feed still lists no fixed versions for four unique findings: PYSEC-2026-311, PYSEC-2026-3813, PYSEC-2026-3814 and PYSEC-2026-3815. No patched stable upgrade was available to test; a downgrade is not a demonstrated fix. Upstream tracking: https://github.com/chroma-core/chroma/issues/7909.

Descriptions concern Chroma HTTP-server model/collection configuration and server authorization. CiteRAG uses embedded PersistentClient, exposes no Chroma server routes, accepts no embedding-function/model-repository configuration from users, and never enables remote model code. The optional cross-encoder loads local files only. This narrows applicability; it does not patch the dependency or prove immunity.

`backend/security/advisory-exceptions.json` retains the exact version/IDs, rationale, invalidating conditions and review deadline **2026-11-29**. The audit saves raw findings and fails for any unreviewed, expired or unusable result. Re-review before upgrading, exposing a server, adding RBAC/multi-tenancy or changing model-loading behavior. Do not silently extend the exception.

## Remaining deployment gates

No public deployment is authorized. Verify Linux container execution and volume permissions, TLS/cookie/origin behavior behind the chosen proxy, backup/restore of both stores and quota state, owner-token storage/rotation, single-replica operation, host resource limits and edge protection before live exposure. Independent human/unseen-document/adversarial evaluation, isolated PDF handling and cross-store crash recovery remain future work. Source publication and passing CI do not establish hosted production readiness.
