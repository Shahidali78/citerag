# Final portfolio verification

Verified locally on Windows on 29 October 2026 (Europe/Rome). No public GitHub push, deployment, paid infrastructure creation or social post was performed. The backend .env and key were preserved; real OpenAI mode remains enabled.

## Actual verification

| Check | Actual result |
| --- | --- |
| Backend tests | 66 passed |
| Python dependency compatibility | No broken requirements |
| TypeScript checking | Passed |
| Next.js production build | Passed; standalone frontend started locally |
| Browser verification | 12 distinct desktop/mobile checks passed across full and targeted runs |
| Real OpenAI integration | Held-out embedding, generation and structured judging completed; real API/browser chat still worked |
| Held-out comparison | 40 questions x 3 fixed methods, 120 outcomes retained |
| Source evidence | Exact quotes, page metadata and acceptable overlapping chunk alternatives validated against public documents |
| Reserved final test | 12 questions; validated as data but not embedded, generated, judged or used for selection |
| Historical reports/dataset | Preserved hashes checked; no historical score overwritten |
| API key handling | Actual configured value absent from publishable candidate files; .env unchanged |
| Git ignores | Verified using Git; environment, database, cache, checkpoint and private-work paths excluded |
| Git source review | Source-only --no-index diffs reviewed; real repository not initialized/committed/pushed |
| npm advisory audit | Zero reported vulnerabilities |
| Python advisory review | No unreviewed findings; four unique unpatched Chroma server advisories retained under documented embedded-only applicability review |
| Compose | Configuration validated |
| Docker Engine | Unavailable; container build/start not executed |
| Hosted Actions/Vercel/Render | Configuration prepared/reviewed; no hosted execution or deployment |

The initial ten-check browser run passed nine and exposed a mobile report-selection response-order race. The page was fixed to ignore stale responses. Two deterministic race checks were added, and the four dashboard/race checks then passed on desktop/mobile. The eight upload/chat/controls/safety workflows had already passed. Read-only rechecks did not incur paid model calls.

## Frozen evaluation and findings

The held-out set contains 32 answerable and eight unanswerable new questions across direct facts, paraphrases, multiple chunks, comparisons, distracting terms, citation support and abstention. A separate final set contains 12 cases. This is question-level evaluation over the same small known corpus, not blind external annotation or unseen-domain testing.

Before new measurements, old development outputs showed five lexical-F1 drops, full reference-token coverage, and longer answers. A shared prompt clarification targeted unrequested verbosity and the false inference that citation IDs prove accuracy. Its exact hash, retrieval settings and source-code hashes were frozen before held-out generation. Threshold .2, models, candidate count, final K and ranking weights were not tuned to held-out answers. Historical-vs-held-out comparisons include new questions, prompt and grading rules.

Dense/hybrid held-out source recall was 1.0 with precision .3875; reranked recall was .8438 with precision .8542. Gold-evidence precision was .2625/.2625/.8542. Answer lexical F1 was .6885/.7083/.6036. Correctness judge means were 1.0/1.0/.8750. Citation identifier validity stayed 1.0 where raw markers were present, while reranked answerable citation coverage was .8750. Six answerable reranked cases lost complete or partial required evidence; four were fully refused.

Strict no-citation abstention was 3/8, 4/8 and 5/8. Many other negative answers acknowledged missing information but cited related facts; this is distinct from inventing the requested fact. Model judgments remain fallible and same-model-family estimates. All applicable judge scores were present, with intended support N/A values excluded and denominators recorded.

One question-embedding batch was reused, with 115 generation calls and 110 judge calls; ten exact judge inputs reused scores. Five filtered outcomes required no generation call. Mean latency excludes shared embeddings and judges. Lower reranked token use partly reflects missing context/false abstention and is not a quality-neutral performance improvement. Paid-work checkpoints and generation caching were tested, including a simulated judge failure and resume without regenerating the answer.

See docs/heldout-results.md and raw docs/heldout/v1 reports. All 143 returned citations in the completed held-out reports were checked against their selected and persisted chunk IDs, text, filenames, and pages. No held-out row was selectively regenerated after inspection, and no final test was executed.

## Publication and deployment status

MIT, architecture, screenshots, installation/configuration, explicit benchmark conditions, monitoring, Docker, deployment guidance, contribution files and credential-free CI are present. Draft repository title/description, five topics, three resume bullets, a LinkedIn announcement and a portfolio description are in docs/portfolio-copy.md. These drafts were not sent or published.

Approval is required before initializing/connecting a public source repository and pushing. Public application deployment remains blocked on access protection, data ownership/isolation decisions, durable storage and runtime validation. The four upstream advisories need continued review; applicability exceptions are not patches. See docs/release-readiness.md, docs/security.md and docs/deployment.md.
