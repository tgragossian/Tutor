# 07 — Application and web

[Contracts index](README.md) · [Structure review](../../../reviews/2026-10-13/structure.md)

## Layers and dependencies

```
web (FastAPI routes: HTML + JSON) ──▶ application (use cases) ──▶ content, verify, store
domain.py: shared records and enums; no framework or ORM imports
```

- **Application services:**
  - `register`, `login`
  - `start_session`, `current_item`, `submit_answer`
  - `advance`, `skip`, `reveal`
  - `session_summary`
- **HTML and JSON routes call the same services.** Neither contains session rules.
- `verify` never imports `web`, `store`, `application` or any LLM client.
- **Construction:** configuration, engine and pool are created in `create_app(settings)`, never when a module is imported. Database sessions are scoped to a request.

## Routes

| Kind | Routes |
|---|---|
| HTML | `/login`, `/register`, `/` (topic picker + history), `/practice/{session_id}` |
| JSON | `/api/auth/*`, `/api/sessions` (POST), `/api/sessions/{id}/current` (GET), `/api/sessions/{id}/{submit,advance,skip,reveal}` (POST) |
| Ops | `/healthz` (process up), `/readyz` (database reachable, content loaded, pool alive) |

- **The HTML problem page** submits through `fetch` to the JSON API and renders the results itself. HTMX is used only where a route deliberately returns HTML fragments. No route mixes JSON and fragments.
- Errors use `{error, message}` with these codes: 401, 403, 404, 409 `stale_item`, 413, 422, 429, 503 `verifier_busy`.

## DTOs

- **Public item:** `session_item_id`, `revision`, `statement_html`, `answer_kind`, `precision_hint`, `choices` (choice kind only), `source` (book, section, exercise, url, license), `allowed_actions`.
- The private fields listed in [02](02-answer-contracts.md) never appear. A test checks every JSON and HTML response against the seed answers' LaTeX and MathJSON.

## Security

- **Passwords:** argon2, 8–128 characters.
- **Session cookie:** signed, `HttpOnly`, `Secure` (except in development), `SameSite=Lax`.
  - It expires after 14 days.
  - The session id is rotated on login.
  - Logout clears it server-side.
- **CSRF** is checked on **every** cookie-authenticated mutation, JSON included. The token is sent as a header or a form field.
- **Rate limits:**
  - In-memory with a sliding window, per process. A single process is assumed, and this is documented.
  - Auth: 10 per minute per IP. Submit: 30 per minute per user.
- **Rendering:**
  - Problem statements are trusted content. They are rendered to HTML at compile time with a Markdown renderer whose raw-HTML support is disabled. Math is rendered by MathLive in read-only mode.
  - User text is never rendered as Markdown.
  - Links are restricted to `https://openstax.org/`.
- **Content Security Policy:** `default-src 'self'`; scripts only from self, plus the SRI-pinned vendor files.
- **Logging:**
  - Structured JSON with the request id, route, status, duration, and the verifier's status, reason, method and timing.
  - Never logged: passwords, cookies, CSRF tokens.
  - Answers are logged in full only at debug level.

## UI (milestone B)

- The topic picker covers the 3 topics, plus a history of past sessions.
- **The problem page shows:**
  - the statement
  - source attribution
  - the MathLive field, with the calculus button row (a/b, xⁿ, √, sin, cos, tan, ln, eˣ, π, |x|) and the built-in keyboard
  - the precision hint
  - Check, Next, Skip (when allowed) and Show answer (when exhausted)
- **Verdict copy:** "Correct" / "Not quite — try again (N left)" / "We couldn't check this automatically. You can try another form or skip."
