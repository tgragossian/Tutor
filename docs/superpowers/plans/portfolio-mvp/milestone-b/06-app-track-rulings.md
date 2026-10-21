# Milestone B: app-track rulings (tasks 10–15)

[Milestone B plan](README.md) · [Execution rulings R7–R24](02-execution-rulings.md) · [Status](03-execution-status.md)

Made during inline execution on 2026-10-21. Each costs little if wrong; Thomas may overturn any.

## Store (task 10, amended in 11–12)

- **A1:** `sqlalchemy==2.1.3`, `alembic==1.20.0`, `argon2-cffi==25.1.0`, `itsdangerous==2.2.0`,
  `python-multipart==0.0.32` pinned exactly; `pycparser` locked to 3.0 (3.1/3.11 are under 14 days old).
- **A2:** timestamps use a `UTCDateTime` type that rejects naive datetimes and restores UTC on
  load (SQLite drops offsets). Enum columns store their values with no CHECK constraint.
- **A3:** SQLite transactions start with `BEGIN IMMEDIATE`, so concurrent writers wait on
  `busy_timeout` instead of failing at once with "database is locked" (review focus 3).
- **A4:** `attempt_results.applied` marks results stored after a lost race (spec 06 step 4).
  Without it a stale result and a real correct result look the same (`counts_as_try` false).
  Added to the never-deployed 0001 baseline.
- **A5:** `upgrade()` creates the SQLite directory; app start never writes to disk.

## Accounts and API (tasks 11, 13)

- **A6:** username/password rule violations are 422 `invalid_input`; usernames are trimmed and
  lowercased. Login failures share one message and verify a dummy hash for unknown users.
- **A7:** every error is `{error, message}`, including 404/405/413 and request validation.
  503 `verifier_busy` sends `Retry-After: 2`; 409 `submission_pending` sends `Retry-After: 1`.
- **A8:** `create_app(settings, *, pool=None)`: without a pool, the `VerifierPool` starts in the
  lifespan and closes on shutdown; tests inject a spy pool.
- **A9:** request logs name verdict fields `verdict_status`, `verdict_reason`, `verdict_method`
  (`method` is the HTTP method). The 16 KB cap is ASGI middleware.
- **A10:** format-issue copy lives in `web/messages.py`; student-facing verifier details are shown
  verbatim (R15) and technical ones rewritten (R16). Thomas may want to review the wording.

## Practice rules (task 12)

- **A11:** selection tiers: unseen (textbook order), then latest result incorrect (oldest first),
  then seen without a usable result (skipped, unable to verify). A skip does not erase an
  earlier result. The item just shown is not repeated while another candidate remains.
- **A12:** skip is allowed whenever the item is active; exhausted allows reveal and advance.
- **A13:** precision hints only on numeric problems. Starting on mastered topics gives a finished
  session (`Done("all_correct")`) rather than an error.
- **A14:** an orphaned reservation (R5) is regraded against the replay's `item_revision`.

## Pages (task 14)

- **A15 (R4):** CSP is `default-src 'self'; style-src-attr 'unsafe-inline'`; MathLive needs
  inline style attributes. Details in [security](../../../../ops/security.md).
- **A16:** SRI on every vendored module (script tags plus `modulepreload`); the vendor folder is
  stored byte-for-byte in git (`-text`).
- **A17:** the topic picker is a plain form posting to `POST /sessions`; page routes render an
  HTML error page; the practice page shows "Tries left: N".

## Browser smoke (task 15)

- **A18:** Playwright's zero-length click does not focus a MathLive field; the smoke clicks with
  an 80 ms press. The smoke and its CI job were committed before the new content.

## Thomas's UI feedback (2026-10-21, after the first deploy)

- **A19:** typing a function name (sin, cos, tan, sec, csc, cot, arcsin, arccos, arctan, ln,
  log, exp) inserts its parentheses with the cursor inside; a habitual "(" right after is
  swallowed. MathLive's auto-closed ")" is drawn solid. Hyperbolic shortcuts are removed.
- **A20:** a session never repeats a problem: it ends (`session_complete`) once every unsolved
  problem in its topics was shown; missed problems return in a later session. The end screen
  says "Next features under construction, thank you for using this tutor!" US spelling.
- **A21:** history lists only sessions with a graded answer; "Start" with the same topics
  reuses the latest untouched open session. "Clear history" (migration 0002, `hidden_at`)
  hides listed sessions but keeps their answers, so progress and selection are unchanged.
