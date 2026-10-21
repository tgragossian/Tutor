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
