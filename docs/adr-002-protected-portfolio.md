# ADR 002: Public replay showcase and protected owner workspace

Status: implemented on feature branch; merge/deployment approval pending.

## Context

The original local workspace exposed corpus and paid model routes without authentication. An anonymous public portfolio must not allow paid inference, private documents, mutation or monitoring. The owner wants to retain real RAG functionality without introducing a full multi-user account platform.

## Decision

Default to an immutable showcase over an explicit public-report allowlist. Replay exact saved hybrid questions/answers with original citations; never instantiate a provider or query private storage. Do not substitute synthetic metrics or new heuristic answers for historical real runs.

For live mode, require an owner-provided high-entropy bearer token in FastAPI's default-deny request policy. Use a same-origin Next.js gateway with a one-hour HttpOnly/SameSite=Strict cookie and an explicit frontend-origin check for mutation. Require Secure cookies on production HTTPS. API authorization remains independent of frontend controls. No secret is generated automatically.

Serialize conservative daily request/token/estimated-cost reservations in a separate SQLite ledger on the durable backend disk. Reserve before real provider calls; cap generation output/context, include retry ceilings and retain failed-call reservations. Missing prices fail closed. Existing content-free usage telemetry remains distinct from reservations and invoices.

## Consequences

The showcase is free of model charges and safe to explore without owner credentials, while live functionality remains available after deliberate setup. Browser scripts do not receive the token. Single-owner secret management is simple but has no per-user isolation, MFA, account recovery or individual revocation. Rotation revokes all sessions.

The gateway adds a server hop, so hosting body/duration limits apply. Vercel's request limit may prevent the backend's full 20 MB allowance; document this rather than claiming hosted upload compatibility. Local SQLite/Chroma imply one process/replica and verified durable storage. Request rate limiting is per-process, not distributed. Pricing and conservative reservations cannot guarantee provider invoices or account-wide cost control.

## Validation

Backend regressions test fail-closed access, direct anonymous requests, private-store isolation, reservation persistence/concurrency and pre-provider denial. A cross-platform offline browser harness tests showcase, login/logout, HttpOnly cookies, origin rejection, uploads, citations, dashboards and responsive layout without owner data or an OpenAI key. CI pins Ubuntu/action revisions and runs these checks without provider secrets.

Historical evaluation artifacts and the reserved final test are unchanged. New runtime output/budget guards are not part of the original benchmark conditions; exact reproduction belongs on its historical commit, not a silently altered protocol.
