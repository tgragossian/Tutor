[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 370–384. Review findings remain unresolved.

## 8. Errors, security, operations

- **Content load:** any schema error, unknown topic, unparseable answer, duplicate id or prerequisite cycle aborts startup with a precise message. A test enforces the same in CI.
- **Auth:**
  - argon2 hashes
  - signed session cookie: `HttpOnly`, `Secure` (except local dev), `SameSite=Lax`
  - CSRF token on state-changing form/HTMX requests
- **Rate limits (in-process):**
  - login and register: 10/min per IP
  - attempts: 30/min per user
- **Secrets:** environment variables only (`SECRET_KEY`, `DATABASE_URL`). `.env` is git-ignored.
- **Logging:** structured JSON with request_id, user_id, route, status, latency, and verdict status/method/latency. Passwords are never logged.

---

<!-- End preserved source. -->
