# Security headers, cookies and CSRF

[Operations](README.md) · [Spec 07](../superpowers/specs/2026-10-13-portfolio-core/07-application-and-web.md)

## Content Security Policy

Sent on every response (including errors) by `SecurityHeadersMiddleware` in `web/app.py`:

Content-Security-Policy: `default-src 'self'; style-src-attr 'unsafe-inline'`

Ruling R4: start from `default-src 'self'` and add only what vendored MathLive needs,
each with its reason below. Scripts stay self-only: no inline scripts, no `unsafe-eval`.

| Addition | Reason |
|---|---|
| `style-src-attr 'unsafe-inline'` | MathLive 0.111.1 lays out formulas with inline `style="…"` attributes (126 violations on the practice page without it, and the field could not be edited). Only style *attributes* are allowed: inline `<style>` elements and all scripts stay blocked. Measured 2026-10-21 in Chromium. |

## Scripts and SRI

- MathLive and Compute Engine are self-hosted under `/static/vendor/`, copied by
  `npm run vendor --prefix tools` (`tools/vendor.mjs`), which writes `manifest.json`.
- Entry modules load with `<script type="module" integrity="sha384-…">`; Compute Engine's
  chunks load with `<link rel="modulepreload" integrity="sha384-…">`, so every vendored module
  is hash-checked. `.gitattributes` stores the vendor folder byte-for-byte (`-text`).
- `tests/integration/test_pages.py` recomputes every hash from the files on disk.

## Cookies and CSRF

- `mt_session`: signed (itsdangerous), `HttpOnly`, `SameSite=Lax`, `Secure` except in
  development, 14 days. The server stores only the SHA-256 of the session token.
- Every cookie-authenticated `POST` (JSON or form) needs the session's CSRF token, as the
  `X-CSRF-Token` header or a `csrf_token` form field. Login rotates the session.

## Other headers

- `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`.

## C1 help: provider processing, logs and the key

- **Provider processing:** when a student asks for help, their attempt text (LaTeX), the
  problem, the chosen confusion label and retrieved textbook passages are sent to Anthropic
  to write the reply. Nothing is sent unless a student presses a help
  button; grading stays local. Spec 09 requires the page to say so in plain language, without promising zero
  retention; it is implemented (`#help-disclosure`, shown only when help is enabled), wording
  pending Thomas's approval. Help text is saved with history and nulled by Clear history.
- **Logs:** request logs and errors never contain student text, model output, chunk text or
  the API key (counts, ids, status and error type only). Usage rows store tokens and cost.
- **Key:** `MATHTUTOR_ANTHROPIC_API_KEY` lives only in the host's `deploy/.env` (mode 600,
  git-ignored), never in git, chat or logs; a console spend limit applies, auto-reload is off.
  See [runbook C1](runbook-c1.md#set-the-anthropic-key). `MATHTUTOR_HELP_GENERATOR=off` disables help.
- **Output:** model text passes the fail-closed leak guard (SymPy, own pool), then is HTML-escaped
  by a local renderer; source links point only to `https://openstax.org/` (checked again in the browser).
  The guard checks extracted math, so prose leakage is reduced, not proven absent.
- **Attribution:** passages are from OpenStax Calculus Volume 1, CC BY-NC-SA 4.0; each cited
  source links to the book and shows the license.
