# Protected portfolio deployment runbook

Configuration is prepared, not deployed. Creating hosting services/disks or enabling a paid plan requires owner approval. Merging the feature PR also requires separate approval.

## Choose the exposure model

**Public showcase:** backend `CITERAG_ACCESS_MODE=showcase`. Only bundled synthetic documents, exact saved responses and genuine saved reports are exposed. No OpenAI key, token or paid inference is needed. Do not expose private runtime monitoring or allow uploads. This is the recommended initial recruiter-facing experience.

**Protected live demonstration:** one API process/replica, durable disk, owner-supplied access token and restricted OpenAI project. All data/model routes are authorized on the backend. The Next.js gateway provides the owner session without revealing credentials to JavaScript. Do not enable live mode until storage, TLS, limits and recovery are verified.

Use Vercel for Next.js and one Render Docker service for FastAPI, or a single host with Docker Compose. The gateway uses a server-only backend origin; browsers always use `/api` on the frontend. Keep the backend private/restricted at the network edge when practical, while retaining API authentication regardless of ingress controls.

## Current provider constraints and estimated costs

Official documentation checked 2026-10-29:

- [Vercel Hobby](https://vercel.com/docs/plans/hobby) is free and limited to personal, non-commercial use. Review whether your portfolio use qualifies; do not start a trial or upgrade automatically. [Pricing](https://vercel.com/pricing) lists Pro at $20/month with usage terms/taxes in addition.
- [Render pricing](https://render.com/pricing?trk=article-ssr-frontend-pulse_little-text-block) lists $7/month for 512 MB and $25/month for 2 GB compute, plus persistent disk at $0.25/GB/month. These are planning estimates, not a checkout quote or guarantee the smallest instance can run Chroma reliably. Measure memory on the actual image/corpus before selecting a plan.
- [Render free-service limits](https://render.com/docs/free) include ephemeral local storage and idle spin-down. Free services cannot attach persistent disks. A free ephemeral service can only be considered for immutable showcase data with no live/private state, accepting cold starts and hosting limits; it is unsuitable for the live corpus/ledger design.
- [Persistent disks](https://render.com/docs/disks) retain only data under the mount and constrain scaling/deployment behavior. The prepared Blueprint retains its paid starter/1 GB disk configuration as an explicit proposal; it has not been applied.

A 1 GB disk plus $7 compute is approximately **$7.25/month**, excluding taxes, bandwidth/build overages and OpenAI; 2 GB compute plus that disk is about **$25.25/month**. Vercel Hobby adds $0 only if eligible/within limits. Live model usage is extra. `DAILY_USD_LIMIT=1` is an application reservation allowance, not a promised $1/day invoice cap. Showcase makes no model calls. Recheck official prices and obtain approval before provisioning anything.

## Backend configuration

Render build context is repository root, Dockerfile `backend/Dockerfile`. It copies only app/sample artifacts and dependencies, including showcase reports; no environment file is baked in. The startup command is:

```sh
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --no-access-log
```

Run **one worker and one replica**. Health check `/health` confirms process/configuration, not provider billing or a paid test. Render terminates public HTTPS; keep the canonical host in `ALLOWED_HOSTS` (the Render-provided external hostname is added automatically).

| Backend variable | Showcase | Protected live |
| --- | --- | --- |
| CITERAG_ACCESS_MODE | showcase | live |
| CITERAG_ACCESS_TOKEN | Not needed | Owner-supplied high-entropy secret, 32+ chars |
| CITERAG_DEMO | Not used by showcase | false for real OpenAI |
| OPENAI_API_KEY | Not needed | Secret in backend host only |
| OPENAI_CHAT_MODEL | Not used | gpt-4.1-mini unless deliberately changed |
| OPENAI_EMBEDDING_MODEL | Not used | text-embedding-3-small; re-index if changed |
| CORS_ORIGINS | Exact frontend HTTPS origin | Same; never wildcard previews |
| ALLOWED_HOSTS | Explicit API hostnames | Same |
| CHROMA_PATH | Unused runtime store | /app/data/chroma |
| SQLITE_PATH | Unused runtime store | /app/data/metadata.sqlite3 |
| EVALUATION_PATH | Bundled reports are used | /app/data/evaluations/latest.json |
| EVALUATION_HISTORY_PATH | Bundled allowlist is used | /app/data/evaluations/runs |
| CHAT_INPUT_USD_PER_MILLION / CHAT_OUTPUT_USD_PER_MILLION / EMBEDDING_USD_PER_MILLION | Not needed | Positive owner-reviewed current model rates |
| DAILY_REQUEST_LIMIT / DAILY_TOKEN_LIMIT / DAILY_USD_LIMIT | No paid calls | Defaults 50 / 200000 / 1; review deliberately |
| MAX_OUTPUT_TOKENS / MAX_CONTEXT_CHARS | Saved examples only | Defaults 800 / 24000 |
| RETRIEVAL_MODE | Saved hybrid examples | hybrid; dense also recommended |
| LOG_QUERY_TEXT / METRICS_RETENTION_DAYS | No private telemetry exposed | false / 30 |

Mount durable storage at `/app/data`, including the `.budget`, `.metrics` and metadata/vector files. UID 10001 must be able to write the mounted directory. Disk ownership is not yet runtime-verified; use host-supported provisioning, not a root-running application workaround. Never copy local private corpus data to hosting implicitly.

## Frontend configuration

Vercel root directory `frontend`, framework Next.js, install `npm ci`, build `npm run build`, Node 22. Server-only environment:

```text
CITERAG_BACKEND_URL=https://your-api-host.example
CITERAG_FRONTEND_ORIGIN=https://your-canonical-frontend.example
CITERAG_LOCAL_HTTP=false
```

Use actual hostnames at deployment; example domains are not resources. Do not set an OpenAI key on Vercel, use NEXT_PUBLIC secrets, or expose the owner token through client variables. `NEXT_PUBLIC_API_URL` is obsolete: the browser uses the same-origin gateway. Configure the exact canonical frontend origin because mutation checks do not trust forwarded host headers or wildcard previews. Test login/cookie handling on HTTPS and on the chosen preview policy. All API data responses are no-store; do not add a shared cache in front of authenticated requests.

Gateway requests time out after 180 seconds; hosting-plan request duration/body limits can be stricter. Vercel Functions currently cap request/response bodies (see [limits](https://vercel.com/docs/functions/limitations)); the backend's 20 MB upload allowance does not override the host limit. Small portfolio files work within the gateway limit; large live uploads require a separately reviewed protected direct-upload architecture or a host with sufficient body limits. Do not claim a hosted 20 MB upload was tested.

## Local Docker verification

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
# After checking health and the UI:
docker compose restart backend
docker compose down
```

Compose defaults to showcase and publishes ports only on 127.0.0.1. The frontend server reaches `http://backend:8000`; browsers reach localhost:3000. Only loopback Compose enables the local HTTP cookie override. Health checks use container loopback and frontend startup waits for backend health. Normal `down` preserves `citerag-data`; do not use `down -v` on valuable data.

Docker Engine was unavailable during this work. Build, container health, non-root volume ownership and persistence across container restart remain unchecked. To verify live persistence later, use disposable data, owner authentication and a fixture provider first, upload a tiny document, record IDs/counts, restart, and compare. Real embedding smoke tests require separate paid-call intent. Never replace the owner's current volume during verification.

## Backup, recovery and rollback

1. Put live mode into maintenance (stop writes and paid calls); stop the backend before copying its full data directory, or take a storage-consistent snapshot. Chroma and SQLite are not a cross-store transaction.
2. Back up vectors, metadata, metrics, evaluation history and usage ledger together. Encrypt/restrict backups; never commit them. Set retention with the owner and inspect legacy query_logs for old private text.
3. Restore to a separate empty volume using the same app/dependency/model versions. Verify document IDs/pages/chunk counts and ledger state before a cited-answer test. Do not reset spending reservations on the active UTC day.
4. Record the immutable application commit/image tag before deployment. For rollback, disable live inference, restore the previous image and compatible data snapshot, then check health, authentication and corpus/ledger consistency. Do not blindly roll back to pre-auth code on a public endpoint; keep showcase-only or private ingress.
5. Monitor sanitized request IDs, 401/403/429/5xx rates, latency, usage and ledger reservations. External error tracking is not configured; if added, scrub bodies, headers, cookies and provider errors before transmission.

## Deployment approval checklist

- [ ] Owner approves merge and the exact hosting/account/paid resources; no deployment performed by this PR.
- [ ] PR CI green; historical reports/datasets unchanged; final reserve unused.
- [ ] Chroma advisories reviewed before their deadline; no Chroma HTTP server/remote model configuration introduced.
- [ ] Images built, non-root volume ownership and restart persistence verified.
- [ ] Canonical HTTPS origins/hosts configured; missing/wrong token denies every private API route.
- [ ] Showcase cannot access private data or instantiate a provider; reports/examples labeled accurately.
- [ ] Owner secret generated/stored privately, not a fixture value; rotation/logout/expiry tested.
- [ ] Live provider prices and quotas reviewed; unknown usage stays reserved; edge limits and one-replica setting confirmed.
- [ ] Host body/duration/memory limits tested with intended demo files.
- [ ] Backup/restore and safe rollback tested; no private data or secrets in images/logs/artifacts.

Only after these gates should an approved protected live endpoint be tested. Passing local/CI checks does not verify the hosting environment.
