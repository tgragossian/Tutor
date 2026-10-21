# API contracts

[Documentation index](../docs/README.md)

Example request and response bodies for the JSON API. Every file in `examples/` is validated
against its pydantic model in `src/mathtutor/web/schemas.py` and must round-trip exactly
(`tests/unit/test_api_contracts.py`, `tests/integration/test_api.py`).

## Routes

| Route | Body | Response |
|---|---|---|
| `POST /api/auth/register`, `/login` | `{username, password}` | `{username, csrf_token}` + `mt_session` cookie |
| `POST /api/auth/logout` | — | `{ok: true}` |
| `GET /api/auth/me` | — | `{username, csrf_token}` |
| `POST /api/sessions` | `StartRequest` | 201 `StartResponse` |
| `GET /api/sessions` | — | list of `SessionSummaryOut` |
| `GET /api/sessions/{id}/current` | — | `CurrentResponse` (read-only) |
| `POST /api/sessions/{id}/submit` | `SubmissionRequest` | `SubmitResponse` |
| `POST /api/sessions/{id}/{advance,skip,reveal}` | `ActionRequest` | `CurrentResponse` |

- Every cookie-authenticated `POST` carries the CSRF token as `X-CSRF-Token` (or a
  `csrf_token` form field); otherwise 403 `csrf_failed`.
- Bodies over 16 KB get 413 `payload_too_large`.
- Errors are `{error, message}`: 401, 403, 404, 409 (`stale_item`, `invalid_action`,
  `submission_pending`, `username_taken`, `unknown_topic`), 413, 422 (`invalid_request`,
  `invalid_input`, `kind_mismatch`), 429 `rate_limited`, 503 `verifier_busy` with `Retry-After: 2`.
- A format issue is a 200 `SubmitResponse` whose `outcome` is `{code, message}`; nothing changes.

## Examples

Requests:
- `submit-expression.json`: MathJSON captured from MathLive and Compute Engine 0.151.0 for
  `6x\cos(3x^2)`, in raw (non-canonical) form.
- `submit-numeric.json`: the captured number `0.785`; MathJSON loses trailing zeros (ADR 0002).
- `submit-choice.json`: only `choice_id`, never MathJSON or LaTeX.
- `start-request.json`, `action-request.json`.

Responses:
- `item-expression.json`, `item-choice.json`: `PublicItem`s (the choice item has an
  author-adapted `source`).
- `start-response.json`; `current-item.json`, `current-revealed.json` (after exhaustion),
  `current-done.json`.
- `submit-response-correct.json`, `-incorrect.json`, `-unable.json`, `-format-issue.json`.
- `error-stale-item.json`, `error-verifier-busy.json`, `error-invalid-request.json`.
- `sessions-history.json`: `GET /api/sessions`.

## Rules

- Public items never contain `latex`, `mathjson`, `correct`, `misconceptions`, `review` or
  `answer`. The expected answer leaves the server only as `revealed_latex`, after a reveal.
- `submission_id` is a UUID version 4; `session_item_id` is greater than 0; `item_revision` is
  at least 0. `latex` is at most 2000 characters; `choice_id` matches `^[a-z]$`.
- `topics` lists 1–3 topic ids. Unknown fields are rejected everywhere.
- Decimals in request bodies are read as exact literals, never floats.
