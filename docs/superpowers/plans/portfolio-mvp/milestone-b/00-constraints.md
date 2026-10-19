# Milestone B — Global constraints, rulings and review focus

[Milestone B plan](README.md) · [Spec](../../../specs/2026-10-13-portfolio-core/README.md)

Updated 2026-10-19: read [execution rulings R7–R21](02-execution-rulings.md) with every task.
They replace conflicting recipes below; [execution status](03-execution-status.md) records completion.

Every task's requirements include this page. Milestone A's [constraints](../milestone-a/00-constraints.md) still apply.

## Global constraints

- **Untrusted input** (student answers, request bodies, eval files) never reaches `eval`, `sympify`, `parse_expr` or `exec`. SymPy objects are built only by `verify/translate.py`.
- **"Correct" requires a proof.** Numeric probes may only refute. No tolerance-based acceptance anywhere.
- **`unable_to_verify` never counts as wrong**, never consumes a try, and always leaves skip available.
- **Exact numbers at every JSON boundary.** Every `json.loads` that can see MathJSON uses `parse_float=as_num` (task 1), which turns a decimal literal into `{"num": "<literal>"}`. No Python `float` ever holds an answer value.
- **Process boundary:** the web process never imports `sympy` or `mpmath`. Translation, pre-check cost estimation and equivalence run only in pool workers (and in the offline content-check and eval CLIs).
- **Dependency rules:** `verify` imports only `domain` and `content`; `store` imports only `domain`; `application` imports `content`, `verify`, `store`, `domain`; `web` imports `application` and below. `domain.py` stays framework-free.
- **Construction at startup:** engine, sessionmaker, verifier pool, rate limiter and services are built in `create_app(settings)`; nothing at import time. The pool is closed on shutdown (lifespan).
- **Limits (spec 03, 05, 07):** body 16 KB → 413; nodes 200; depth 30; integer ≤ 30 digits; decimal ≤ 30 significant digits, exponent within ±30; deadline 3 s; queue 8; queue wait 2 s; `RLIMIT_AS` 384 MB (Linux only); auth 10/min/IP; submit 30/min/user; 3 tries.
- **Versions recorded on every result:** `content_version`, `verifier_version` (`<__version__>+<git sha>`, sha from `MATHTUTOR_GIT_SHA`, default `dev`).
- **New dependencies** are added with `uv add` / `npm install --save-exact` and committed locks; no version newer than 14 days unless a security fix (record why in the commit body).
- **Docs:** ≤ 100 lines per Markdown file, linked from a parent index. **Commits:** conventional prefixes, no co-author trailers.

## Rulings made while planning (each costs little if wrong)

- **R1 — Content math is checked offline, not at app startup.** Spec 01's translator-dependent loader errors run in `python -m mathtutor.verify.content_check`, called by CI and by the Docker build. The web process stays SymPy-free (spec 05) and still never serves an unchecked bundle, because the image cannot be built from one.
- **R2 — Server-side login sessions.** A `web_sessions` table (not in spec 06's list) holds a hashed token, user, CSRF token and expiry, so logout can clear a session server-side and login can rotate it (spec 07).
- **R3 — `statement_html` is produced by the Node compiler** with markdown-it (`html: false`); `$...$` becomes `<math-field read-only>` with escaped LaTeX. The bundle's `schema_version` becomes 2.
- **R4 — CSP:** start from `default-src 'self'`. If vendored MathLive needs `style-src 'unsafe-inline'` or `font-src`/`worker-src` entries, add exactly those and record the reason in `docs/ops/security.md`; scripts stay self-only.
- **R5 — Interrupted submissions:** a `submissions` row with no `attempt_results` older than 10 s is regraded on replay instead of returning nothing (review focus 2).
- **R6 — Demo account and nightly reset move to milestone D**; open registration is enough for the milestone B demo.

## Review focus

Failure modes the spec implies but no task's main tests target. Each line names the task that pins it.

1. **A decimal becomes a float somewhere** (request body, compiled content, eval file), so `0.1`, `2.675` or a 30-digit decimal grades wrongly at a rounding boundary.
   Expected: every path yields the exact literal. Pinned by: task 1 (`as_num` on all loaders), task 13 (`test_submit_preserves_decimal_literal`).
2. **A submission is reserved but never graded** (worker crash plus process restart between transactions A and B), and the replay returns 500 or an empty result.
   Expected: the replay regrades (R5). Pinned by: task 12 (`test_replay_regrades_orphaned_reservation`).
3. **SQLite raises "database is locked" under concurrent submits**, surfacing as 500s.
   Expected: WAL plus `busy_timeout` 5000 ms; 16 concurrent submits give only 200/409/503. Pinned by: task 10 (pragmas test), task 12 (`test_sixteen_concurrent_submits`).
4. **Vendored MathLive silently fails under the CSP** (inline styles, fonts), so the field never becomes editable.
   Expected: the field accepts typing and the console shows no CSP violation. Pinned by: task 15 browser smoke.
5. **Refresh or a second tab changes timing or leaks the answer.** Expected: `served_at` is unchanged by any GET, and no GET response contains private fields. Pinned by: task 12 (`test_current_is_read_only`), task 13 (leak test).
