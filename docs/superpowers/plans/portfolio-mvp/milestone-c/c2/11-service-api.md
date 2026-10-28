# C2 tasks 3–4: service and API

[C2 plan](README.md) · Previous: [foundation, pipeline](10-foundation-pipeline.md) · Next: [UI](12-ui.md)

### Task 3: HelpService accepts questions; clearing history scrubs them

**Files:** Modify `help/service.py`, `help/messages.py`, `application/practice.py`
(`clear_history`). Test: `tests/unit/help/test_service.py`,
`tests/integration/test_help_races.py`, `tests/unit/application/test_practice.py`.

**Interfaces:**
- Consumes: Task 1 `normalize_question`, `QuestionRejected`, `cfg.question`; Task 2
  `HelpPipeline.run(..., question=)`, `PipelineResult.use_case`.
- Produces: `HelpIn.question: str | None = None` (raw text); `CLEARED_HASH = "0" * 64` in
  `help/service.py`; messages `QUESTION_INVALID = "Type a question (up to 500 characters)."`
  and `QUESTION_ONLY = "Only a question request takes question text."`

Rules:
- `_validate_fields`: `question` type → `normalize_question(raw, cfg.question.max_chars)`;
  `QuestionRejected` → `InvalidInput(QUESTION_INVALID, code="invalid_question")`. Any other
  type with `question` not None → `InvalidInput(QUESTION_ONLY, code="invalid_question")`.
  `question` with `confusion` → the existing `CONFUSION_ONLY_EXPLAIN` error.
- Disabled by config (`cfg.question.enabled` false) → `unknown_help_type`, like an unknown type.
- `_payload_hash` adds `"question": <normalized>` **only** for question requests, so every
  C1 hash is unchanged. Hash the normalized text, so whitespace variants replay.
- `availability`: append `"question"` after `"explain"` when enabled and the item is open.
- `_Admitted.question: str | None`; `_work` passes it to `pipeline.run`.
- `_finalize_once`: wherever it fills the pending row's metadata, also set
  `row.use_case = result.use_case` (content-free; kept when stale). Never store the question.
- The `help finished` log line gains `use_case=%s` (the label or `-`), nothing else.
- Q1: a delivered question with `asked_for_more` gets `messages.MORE_DETAIL_WARNING` ("This may reduce how much you learn from this problem. I'd recommend trying smaller steps first.")
  as its first paragraph, added by the server before storing and rendering; the row
  records `asked_for_more`. Test: `test_asked_for_more_prepends_the_warning`.
- `clear_history`: in the same update, rows with `help_type == "question"` also get
  `payload_hash = CLEARED_HASH`. A later reuse of such an id is a `Conflict` (409).
- Ladder: unchanged code already advances only for `help_type == "hint"`; pin it with a test.

- [ ] **Step 1: Failing tests**
  - `test_question_delivered_records_use_case`: scripted reply with `use_case="explain"` →
    `DELIVERED`, row `use_case == "explain"`, row has no column containing the question text.
  - `test_question_does_not_advance_ladder`: after a wrong answer, a delivered question leaves
    `hint_counts`, `hint_type`, `hint_attempt_pk` unchanged; never sends `HINT_CHOICE_SCHEMA`.
  - `test_question_validation_codes`: empty, 501 chars, `\x07`, question on `hint` → each
    `InvalidInput` with `code == "invalid_question"`; no row, no ledger entry.
  - `test_question_replay_same_text_and_conflict_on_other_text`.
  - `test_question_disabled_by_config`: `question.enabled=false` → `unknown_help_type`, and
    `availability().types` lacks `"question"`.
  - `test_question_and_hint_serialize_on_item` (races file): a question in flight → a hint on
    the same item returns `PENDING`; submit during a question → question finalizes `STALE`.
  - `test_clear_history_scrubs_question_hash` (practice test): after clear, question rows'
    `payload_hash == CLEARED_HASH`; hint rows keep theirs; reuse of the question id → `Conflict`.
- [ ] **Step 2:** `uv run pytest -q tests/unit/help/test_service.py tests/integration/test_help_races.py tests/unit/application/test_practice.py` → new tests FAIL.
- [ ] **Step 3:** Implement the rules above.
- [ ] **Step 4:** Same command → PASS; full suite, `ruff`, `mypy src`.
- [ ] **Step 5:** Commit `feat(c2): question requests in HelpService; clear scrubs their hash`.

### Task 4: `/api/help` takes `question`; nothing leaks into logs

**Files:** Modify `web/api.py`, `contracts/examples/item-help.json` (add a question example).
Test: `tests/integration/test_help_api.py`, `tests/integration/test_no_leaks.py`,
`tests/integration/test_request_log.py`.

**Interfaces:** consumes Task 1 `HelpRequest.question`, Task 3 `HelpIn.question`. The
response shape is unchanged (no `use_case` to the browser: labels are for measurement).

- [ ] **Step 1: Failing tests**
  - `test_help_question_round_trip`: POST `help_type="question"` with scripted delivery →
    200, `status == "delivered"`, sources resolved; `GET` of the item lists `"question"`.
  - `test_help_question_bounds`: 500 chars → 200; 501 → 400 `invalid_question`;
    2,001 chars → 422 (body cap); `question` on `hint` → 400 `invalid_question`.
  - `test_question_text_never_logged_or_stored`: question `"zebra-sentinel-41 why chain"`;
    the sentinel appears in no captured log record, no request-log JSON line, no column of
    any table (scan every text/JSON column of every row), and not in the response.
  - CSRF and ownership: reuse the C1 parametrized tests with `help_type="question"`.
- [ ] **Step 2:** `uv run pytest -q tests/integration/test_help_api.py tests/integration/test_no_leaks.py tests/integration/test_request_log.py` → FAIL.
- [ ] **Step 3:** Map `body.question` into `HelpIn`; `request.state.log` stays type + status.
- [ ] **Step 4:** Same command → PASS; full suite; `uv run python tools/check_docs.py`.
- [ ] **Step 5:** Commit `feat(c2): /api/help accepts item-scoped questions`.
