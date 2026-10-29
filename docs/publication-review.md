# Public source publication review — 2026-10-29

Proposed repository: `Shahidali78/citerag`, public, MIT. The owner confirmed this exact public repository and account after reviewing the candidate files. GitHub CLI authentication has been renewed through browser authorization and the GitHub API confirms Shahidali78. Local Git initialization is authorized; the reviewed initial commit will contain only the listed source artifacts. No application deployment is authorized.

## Publication contents

The complete candidate list is [publication-files.txt](publication-files.txt). It includes the existing application, MIT license, README with architecture diagram, six public-sample screenshots, backend and browser tests, frozen evaluation datasets and complete real/demo reports with split labels, dependency locks, CI, and deployment instructions. Only the three bundled synthetic documentation fixtures are included; user uploads, databases, runtime logs, caches, credentials, local review files and evaluation checkpoints are excluded.

## Security results

- The configured OpenAI key was checked against every candidate file without displaying its value. No match was found. Common OpenAI/GitHub/AWS credentials, private-key headers and credential-bearing URLs also produced no findings. This is a bounded pattern scan, not proof against every possible secret; dedicated gitleaks/trufflehog executables were unavailable.
- Git ignore checks exclude both real environment files, SQLite/Chroma data, logs and local review artifacts. Only sanitized environment examples are candidates. The backend `.env` remained byte-for-byte unchanged.
- Before publication preparation, this directory and its parents had no project Git repository or prior project commits/history to expose. An ignored temporary, uncommitted Git metadata directory was used solely to validate the candidate list and ignore rules. Before the initial push, inspect the actual staged tree and initial commit again; do not use an unrelated existing repository or import private history.
- npm audit: zero vulnerabilities across all reported severities. Python scoped audit: zero unreviewed findings, **four unpatched ChromaDB 1.5.9 advisories** under the existing embedded-only applicability review, expiring for review on 2026-11-29. This is not a clean vulnerability audit. See [raw report](publication-dependency-audit.json), [exceptions](../backend/security/advisory-exceptions.json) and [security notes](security.md).
- Authentication for public document/paid API routes remains absent. The application is for local single-user use. Source publication does not authorize publicly exposing it.

## Verification

- Backend pytest: **66 passed**; pip check: no broken requirements.
- TypeScript check and Next.js production build: passed.
- Playwright: **12 passed**, desktop/mobile, including two real OpenAI ingestion/chat/citation workflows, dashboard history and delayed-response regression.
- Backend health confirms real OpenAI mode. Hybrid is the running default. Dense and hybrid are recommended; aggressive reranking is labeled experimental in the UI and documentation.
- Frozen datasets, source/prompt/corpus protocol and original protected reports verified without re-running the paid benchmark. The final 12-question reserve remains unexecuted.
- Local workspace, evaluations and API docs: HTTP 200. Screenshots refreshed from public sample data without chat calls.
- Compose configuration validates. Docker Engine is unavailable, so image builds and container execution remain unverified. GitHub-hosted CI has not run; its workflow is included.

## Honest evaluation claims

On the frozen 40-question assessment over the known five-chunk corpus, dense and hybrid retained 100% source recall; aggressive reranking retained 84.38%, while increasing filename precision from 38.75% to 85.42%. It fully refused four of 32 answerable questions. These are question-level holdouts over known documents, not unseen-document generalization. The 16-question calibration results are explicitly in-sample. No unfavorable output was regenerated, no threshold retuned, and no metric fabricated. The operational default was subsequently changed to hybrid; the frozen study and historical reports remain unchanged.

Verdict: exact account/repository confirmation and valid GitHub authentication are complete; source publication may proceed after the staged-tree check. Public application deployment remains blocked and is outside this authorization.
