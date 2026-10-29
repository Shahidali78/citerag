# Final source review

Reviewed the existing application plus new evaluation modules and source-only Git --no-index changes. The project directory has no real Git repository yet; a temporary ignored Git metadata directory was used to validate ignore behavior and inventory candidates. There are no source commits, remotes or pushes from this work.

## Blockers for a public service

Authentication/access protection is missing for document and paid-model routes; CORS and per-process limits are not authorization. Durable storage, Linux volume permissions, hosted HTTPS/CORS, backup/restore and Docker execution are unverified. Four unpatched Chroma server advisories retain the documented embedded-only, version-scoped applicability exception. The fixed reranker loses recall on the new holdout, so its in-sample score must not be marketed as a general guarantee.

## Should fix before stronger production claims

Develop and validate a retrieval policy on development data rather than retuning to the newly observed held-out answers. Add human-reviewed and unseen-document evaluations. Clarify the desired abstention policy when no answer is known but the model cites related facts. Keep the reserved final test unused until a new implementation is frozen. Resume/checkpoint guards and data/prompt/source hashes now prevent common evaluation leakage and unnecessary repeat calls.

The observed dashboard response-order race was fixed with a request-sequence guard and deterministic delayed-response tests. The old answer verbosity/citation-overclaim issue received a predeclared, shared prompt clarification before held-out measurement. No score was manually corrected or unfavorable held-out example regenerated after inspection.

## Nice to have

Split long evaluation orchestration into smaller lifecycle helpers, retain its checkpoint/protocol tests, add broader deployment/load tests, and consider an independently provisioned cross-encoder only under a separately calibrated protocol. The current orchestration keeps checkpoint, resume, integrity and reporting transitions explicit; its size is a maintainability tradeoff, not a hidden network loop.

The existing upload/citation UI, source metadata, model integration, privacy-aware telemetry and original benchmark remain intact. The new quoted gold evidence, negative cases, applicable denominators and raw outputs make the actual precision/recall tradeoff reviewable.

Verdict: Ship after blockers. Source publication with honest limitations requires owner approval; a public paid/upload service must wait for access protection and deployment validation.

Client update: Local implementation and verification are complete; the held-out study exposed a real recall tradeoff, and publication/deployment approval has not been exercised.

## Source publication gate

The owner has conditionally approved public source publication. The newer [publication review](publication-review.md) records fresh checks and the hybrid default. Creation and push still require confirmation of the exact GitHub account/repository and valid authentication. Public deployment is not authorized.

The owner subsequently confirmed public repository Shahidali78/citerag, and browser authentication was verified against the GitHub account API. This authorizes source creation/push only.
