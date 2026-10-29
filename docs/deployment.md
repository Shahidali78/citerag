# Deployment preparation

Nothing has been pushed, made public, deployed, or provisioned. The files below are prepared locally. Review the actual hosting price and access protection before approving resource creation.

## Practical topology

Use Vercel for the frontend and one Render Docker web service for FastAPI, with a persistent disk holding Chroma, document metadata, metrics, and evaluation history. A small VM running Docker Compose is another straightforward single-host option. Keep one API process/replica because local SQLite and Chroma files are not shared distributed databases.

Render documents that only data under the disk mount survives redeploys and restarts, and disk-backed services cannot scale to multiple instances. See [persistent disk constraints](https://render.com/docs/disks). Free Render services cannot attach persistent disks and spin down after idle time; they are unsuitable for this persistent local-store design. See [free service limitations](https://render.com/docs/free).

Budget for backend compute, disk storage, OpenAI usage, and the frontend plan appropriate to your usage. Choose the instance size after measuring memory with your corpus. An optional cross-encoder needs substantially more RAM than the tested lightweight reranker. Verify current amounts on [Render pricing](https://render.com/pricing) and [Vercel pricing](https://vercel.com/pricing); no paid resources were created and no fixed monthly cost is promised here.

## Render backend steps after approval

1. Review the public repository contents and security exception first. Do not publish .env, private documents, databases, or private evaluation files.
2. Import `render.yaml` as a Blueprint or create one Docker web service using build context `backend` and Dockerfile `backend/Dockerfile`. Blueprint fields follow the [official reference](https://render.com/docs/blueprint-spec).
3. Choose a paid instance suitable for the measured workload. The prepared Blueprint starts with the starter plan and a 1 GB disk at `/app/data`; those are explicit paid resources, not a free deployment. Increase memory if needed.
4. Set OPENAI_API_KEY as a secret, CITERAG_DEMO=false, and CORS_ORIGINS to the exact HTTPS frontend origin without a trailing slash. Include the API HTTPS origin as a second explicit origin if using Swagger Try it out behind a TLS-terminating proxy. Render's external hostname is accepted automatically; set ALLOWED_HOSTS explicitly if using a custom API hostname.
5. Keep CHROMA_PATH=/app/data/chroma, SQLITE_PATH=/app/data/metadata.sqlite3, EVALUATION_PATH=/app/data/evaluations/latest.json, and EVALUATION_HISTORY_PATH=/app/data/evaluations/runs. Configure retention, request limits, timeout, and pricing only with reviewed values.
6. The image runs as UID 10001. Verify the mounted disk is writable by that UID before accepting the service. Disk ownership on a hosting platform is not verified locally; resolve ownership through the platform's supported provisioning procedure if it differs. Do not make the application root-owned as a workaround.
7. Use /health as the health-check path. The image binds PORT supplied by the host. HTTPS is terminated by the platform. Health confirms process/configuration, not a live OpenAI charge or valid billing.
8. Upload sample documents through the protected UI and verify an answer, a PDF page citation, monitoring usage, deletion, and persistence after restart. New deployments start with empty data; local Chroma files are not silently uploaded.

## Vercel frontend steps after approval

1. Import the same repository and set Root Directory to `frontend`, framework Next.js, install command `npm ci`, and build command `npm run build`. See [monorepo configuration](https://vercel.com/docs/monorepos).
2. Set NEXT_PUBLIC_API_URL to the public HTTPS backend origin before building. This is a browser-reachable URL, never `http://backend:8000`. Keep the OpenAI key off Vercel frontend environment variables and browser code.
3. If NEXT_PUBLIC_API_URL changes, make a new deployment: public variables are build-time values. See [Vercel environment variables](https://vercel.com/docs/environment-variables).
4. Set the backend CORS_ORIGINS to that exact frontend origin. Do not allow arbitrary preview domains with a wildcard. Configure preview access deliberately.
5. Before public traffic, put both frontend and API behind access protection for the intended single user. Protecting only the UI leaves the unauthenticated API reachable. CORS, trusted hosts, and per-process rate limits are not authentication or a spending quota.

## Local Docker commands

With Docker Desktop's Linux engine running and backend/.env configured:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open http://localhost:3000. Compose publishes both services only on loopback. The browser uses localhost:8000 on the host; no frontend server-side request requires a Docker service hostname. Container health checks correctly use loopback inside their own container. If adding server-side API fetching later, use the backend service hostname internally and keep the public browser URL separate.

Run a saved evaluation after uploading the sample corpus:

```powershell
docker compose exec backend python -m app.eval.run --dataset evals/sample.jsonl --judge
```

Evaluation output and history live on the data volume. Docker volume deletion is destructive; normal `docker compose down` preserves it. Do not run `down -v` on a database you need.

## Verification and operations

Compose configuration validated locally. Docker Engine was unavailable, so images, container health checks, Linux volume ownership, and hosted deployment have not been executed. The same standalone frontend artifact was started and exercised locally with browser tests; that does not substitute for a container test.

For backups, stop writes before copying the full data directory or use a storage snapshot with SQLite-consistent handling. Restore and verify document counts, IDs, vectors, and a cited answer on a separate instance. Chroma/SQLite are not a cross-store transaction, so preserve both together. Keep disk snapshots and an application-level restore test.

Metrics default to 30-day retention and no raw questions. Existing legacy query_logs from older versions may still contain private questions; review their retention separately. OpenAI receives document chunks for embeddings and selected evidence for generation. Configure provider data handling to suit the documents you upload.

If the local disk, embedding model, reranker model, or chunking policy changes, re-index/calibrate and rerun evaluations. Upgrading to multi-user production requires tenant-scoped authorization, per-user data isolation and quotas, durable shared services, distributed rate limiting, background jobs, migrations, and load tests. Those assumptions have not been silently added.

## Current evaluation gate

The fixed reranked filter achieved 84.38% source recall on the new question-level holdout, despite 100% recall on its small calibration benchmark. Its higher precision is a recall tradeoff, not a generally validated improvement. After the frozen study, the source-publication configuration defaults to hybrid; dense is also recommended. Aggressive reranking remains experimental, with its threshold unchanged. This operational recommendation does not change historical results or the frozen protocol. Further retrieval policy work needs development data and a separately frozen assessment; the reserved final set has not been run. See docs/heldout-results.md before making reliability claims or exposing a service.
