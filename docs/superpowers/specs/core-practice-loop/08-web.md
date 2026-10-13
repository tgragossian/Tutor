[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 329–369. Review findings remain unresolved.

## 7. Web layer

### 7.1 Pages (Jinja + HTMX; MathLive pinned and self-hosted under `static/vendor/`)

1. Login / register
2. Dashboard: per-topic recall and application bands, "Start session"
3. Session setup: topics grouped by area, minutes (15/30/45/60/custom 5–180), mode, exam conditions, warm-up toggle
4. Item page:
   - statement, MathLive field, calculus button row (a/b, xⁿ, √, sin, cos, tan, ln, eˣ, π, |x|, ∞, +C, DNE) and MathLive's virtual keyboard
   - precision hint, Check button, verdict area, reason line
   - formula-sheet panel when exam conditions allow
5. Session report

### 7.2 JSON API

| Method & path | Body / returns |
|---|---|
| `POST /api/auth/register`, `/api/auth/login`, `POST /api/auth/logout` | `{username, password}` (password 8–128 chars) |
| `GET /api/topics` | topic tree |
| `POST /api/sessions` | `{mode, topics, minutes, exam_conditions, warmup}` → session |
| `GET /api/sessions/{id}/next` | `{item, reason}` or `{done: true}` |
| `POST /api/attempts` | `{session_id, item_id, answer_mathjson, answer_latex}` → `{verdict, can_retry, can_reveal}` or a format message |
| `POST /api/sessions/{id}/skip-warmup` | turns off the warm-up for this session |
| `POST /api/sessions/{id}/reveal` | expected answer (practice only, after 3 tries) |
| `GET /api/sessions/{id}/report` | per-topic bands + item list |
| `GET /api/me/mastery` | dashboard data |
| `GET /healthz` | `{status: "ok"}` |

Errors use the format `{error: <code>, message: <text>}`.

| Status | Meaning |
|---|---|
| 401 | unauthenticated |
| 403 | another user's session |
| 404 | not found |
| 409 | not the current item / session ended |
| 422 | validation |
| 429 | rate limited |

---

<!-- End preserved source. -->
