# Task 13: JSON API, errors, logging, readiness

[Milestone B plan](../README.md) · [Spec 07](../../../../specs/2026-10-13-portfolio-core/07-application-and-web.md) · [Spec 02](../../../../specs/2026-10-13-portfolio-core/02-answer-contracts.md)

**Status (2026-10-21):** complete in abda25e.
Completed recipe below; [app rulings A1–A18](../06-app-track-rulings.md) record amendments.
Validation is recorded in [evidence](../07-verification-evidence.md); commands below are the execution recipe.

R15/R16: map every FormatIssue to friendly copy, preserving the `e·(x+1)` suggestion.

**Files:**
- Create: `src/mathtutor/web/api.py`, `src/mathtutor/web/logging.py`
- Create: `tests/integration/test_api.py`, `tests/integration/test_no_leaks.py`, `tests/integration/test_process_boundary.py`
- Modify: `src/mathtutor/web/app.py`, `web/schemas.py`, `contracts/README.md`, `contracts/examples/*.json`

**Interfaces:**
- Consumes: `PracticeService`, `ItemView`, `SubmitView`, `Done` (task 12); `current_user`, `require_csrf`, rate limiters (task 11); `loads_exact` (task 1); `check_structure` (task 2).
- Produces (`web/schemas.py` additions; `SubmissionRequest` unchanged; `PublicItem` gains `tries_left: int`, which the verdict copy needs and spec 07 does not forbid):
  - `class StartRequest: topics: list[str]` (1–3 known topic ids) → `{session_id}`
  - `class ActionRequest: item_revision: int`
  - `class VerdictOut: status, reason, method`; `class FormatIssueOut: code, message`
  - `class SubmitResponse: outcome: VerdictOut | FormatIssueOut; item: PublicItem; replayed: bool`
  - `class CurrentResponse: item: PublicItem | None; done: bool; reason: str | None; revealed_latex: str | None`
  - `def to_public(view: ItemView) -> PublicItem` (choices become `PublicChoice(id, label_latex)`)
- Routes (all JSON bodies ≤ 16 KB else 413, checked from `Content-Length` and the read body):
  - `POST /api/sessions` → 201 `{session_id}`
  - `GET /api/sessions/{id}/current` → `CurrentResponse`
  - `POST /api/sessions/{id}/submit` → `SubmitResponse` (200), 409 `stale_item` or `submission_pending` (R13, `Retry-After: 1`), 422 kind mismatch / bad payload, 429, 503 `verifier_busy` with `Retry-After: 2`
  - `POST /api/sessions/{id}/{advance,skip,reveal}` → `CurrentResponse`
  - `GET /api/sessions` → session summaries (history)
  - `/readyz` now also requires: a `SELECT 1` succeeds and `pool.alive()`; otherwise 503 with the failing `reason`.
- Submit body handling: read raw bytes; `loads_exact`; validate with `SubmissionRequest`; run `check_structure` on `mathjson` in the web process (cheap) before the pool; map to `SubmittedAnswer`.

- [x] **Step 1: Write the failing tests.**

```python
def test_full_loop_over_json(client_logged_in): ...   # start → current → wrong answer → retry → correct → advance → next item
def test_submit_preserves_decimal_literal(client_logged_in): ...  # body text with -0.5835 reaches check() as {"num": "-0.5835"} (spy)
def test_body_over_16kb_is_413(client_logged_in): ...
def test_kind_mismatch_is_422(client_logged_in): ...
def test_too_large_tree_rejected_before_pool(client_logged_in): ...   # 201-node sum → FormatIssueOut input_too_large; pool spy not called
def test_busy_is_503_with_retry_after(client_logged_in): ...
def test_submit_rate_limit_30_per_minute(client_logged_in): ...
def test_contract_examples_round_trip(): ...           # every contracts/examples/*.json validates against its model
def test_readyz_503_when_pool_dead(client): ...
def test_no_private_fields_anywhere(client_logged_in):
    # walk every JSON route (and, after task 14, every HTML page) through a whole session;
    # assert no seed answer latex (len ≥ 4), no expected mathjson dump, no "correct", "misconceptions", "review" keys,
    # except the reveal response's revealed_latex after exhaustion
def test_web_process_has_no_sympy(): ...               # subprocess: create_app(settings); assert "sympy" not in sys.modules
def test_request_log_is_json_without_secrets(client_logged_in, capsys): ...  # request_id, route, status, duration_ms, verdict fields; no cookie/csrf/password
```

- [x] **Step 2:** Run `uv run pytest tests/integration -q`. Expected: the new tests FAIL.
- [x] **Step 3: Implement** the router, the body-size guard, the mapping functions, and `web/logging.py`: a pure ASGI middleware that assigns `request_id` (uuid4 hex, echoed as `X-Request-ID`) and emits one JSON line per request with route template, status and `duration_ms`; the submit route adds `verdict_status`, `verdict_reason`, `verdict_method`, `worker_ms`, `queue_ms` (A9) via `request.state`. Answers are logged only at DEBUG.
- [x] **Step 4:** Update `contracts/examples/` with `start`, `current`, `submit-response-*`, `error-*` files and list them in `contracts/README.md`.
- [x] **Step 5:** Run `uv run pytest -q && uv run mypy src && uv run ruff check .`. Expected: PASS.
- [x] **Step 6: Commit** `feat: JSON practice API, structured request logs, readiness checks`.
