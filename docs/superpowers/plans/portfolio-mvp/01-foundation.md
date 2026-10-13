# A — contracts and deployed skeleton

[Plan index](README.md) · Budget target: 20 hours · [Executable tasks](milestone-a/README.md)

## Deliver

1. Scaffold Python/uv/FastAPI, a health endpoint, configuration and CI.
2. Capture real MathLive/Compute Engine inputs with pinned patched versions.
3. Hand-author six representative seed problems, two per chosen topic.
4. Define content, answer, submission and item-presentation contracts.
5. Build a minimal container and HTTPS skeleton with reproducible local startup.

Use the [structure proposal](../../../reviews/2026-10-13/structure.md) without
scaffolding unrelated future components. Preserve developer-authored material.

## Decisions the spike must settle

- Exact MathJSON encoding, noncanonical capture and safe rendering.
- Expression grammar and supported real-domain templates.
- Constants, function arity, negative real roots and numeric precision.
- One semantic answer payload, with an answer-kind discriminant.
- Whether the MVP can avoid any custom LaTeX parser.
- Public item response fields versus private expected-answer fields.
- SessionItem identity, retry states and submission idempotency.

Retain the source AST's restrictions before simplifying.
Write the content schema before implementing broad per-type checkers.
Use human-reviewed structured answers; extracted strings are not automatically trusted.

## Proposed minimum records

- Problem: id, version, topic, source/provenance, statement, answer spec, review evidence.
- AnswerSpec: kind, structured expected value, variables, real domain, optional strict override, precision.
- SessionItem: id, session, problem/version, sequence, state, served/completed timestamps.
- Submission: unique id, session_item_id, semantic answer, creation timestamp.
- AttemptResult: submission id, status, method, reason, verifier version and duration.

Store real intervals/exclusions plus supported-function assumptions.
Use the shared default: equality on that domain, ignoring provably removable holes.
Define the bounded polynomial implicit contract now; implementation comes with topic expansion.
See the [decisions](../../../decisions/0001-delivery-verifier-attribution.md).
Full mathematical domain inference is not an MVP requirement: abstain outside supported cases.
A human reviewer checks that each problem's expected answer matches its statement.

## Exit evidence

- Six source-attributed fixtures load; unsupported schemas fail with useful messages.
- Captured browser payloads round-trip and include malformed/partial cases.
- A small documented contract example is shared by frontend and API tests.
- CI runs meaningful schema/input checks; no feature is claimed implemented prematurely.
- Container starts and health check works locally; HTTPS skeleton works when configured.
- No cloud credentials or account passwords enter Git.
