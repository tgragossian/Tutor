[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 780–825. Review findings remain unresolved.

### Task 16: Session and attempt API

**Files:**
- Create: `src/mathtutor/web/flow.py` (the glue: building `PolicyContext`, deciding when an item is finished, converting rows to `AttemptRecord`), `src/mathtutor/web/api.py`, `tests/web/test_session_api.py`

**Interfaces:**
- Consumes: Tasks 7, 8, 11–15.
- Produces the §7.2 endpoints, plus `POST /api/sessions/{id}/skip-warmup`, which sets `warmup_enabled=False`.
- In `flow.py`:
  - `def item_finished(mode: Mode, attempts_on_item: Sequence[Attempt]) -> bool`
    - diagnostic: after 1 attempt
    - otherwise: after a correct attempt, a revealed attempt, or 3 attempts
  - `def next_selection(db, bank, session, now) -> Selection`
    - Seeds `random.Random(session.id)` and builds `PolicyContext`.
    - On `None`, it ends the session.
    - Otherwise it sets the current item.
- **`POST /api/attempts` flow:**
  1. Check ownership → 403.
  2. If the session has ended, or the item is not current, or the item is already finished → 409 `not_current` (Review Focus 5).
  3. Call `pool.check`.
  4. A `FormatIssue` → 200 `{format_issue: {code, message}}`; no attempt is recorded.
  5. Otherwise record the attempt with `seconds_spent = now − current_item_served_at`. Fill in `is_first_attempt` and `attempt_number`, and use `bank.item_version`.
  6. In diagnostic mode, the response leaves out the verdict: `{recorded: true}`.
  7. In other modes it returns `{verdict, can_retry, can_reveal}`.
- **`next`:** if the current item is not finished, return it again, so a page refresh is safe. Once time is up, the in-progress item is still graded (Review Focus 4).
- **Responses never include the expected answer,** except from `/reveal`.
- **`/reveal`:** practice only, problems only, after 3 tries. It records `revealed=True` on the last attempt and returns `{answer_latex}`, where `answer_latex = sympy.latex(parse_expected(spec))`.

- [ ] **Step 1: Write the failing tests:**
  - **Full flows** via `TestClient`, with a temp DB, the seed content and `verifier_workers=1`:
    - diagnostic → report (bands per topic)
    - practice with warm-up → skip-warmup → wrong ×3 → reveal → next
    - recap
  - another user's session → 403
  - submitting a non-current item → 409
  - **Review Focus 5:** a double submit after a correct answer → 409, and the attempt count is unchanged
  - **Review Focus 4:** with the time budget expired mid-item (inject a clock via `app.state.clock`), the submit is graded and `next` returns `{done: true}`
  - **Format issues:** a format issue records no attempt
  - **No answer leaks:** none of the `/next` payloads contain the expected answer string
- [ ] **Step 2:** Run `uv run pytest tests/web/test_session_api.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement. The clock is `app.state.clock: Callable[[], datetime]`, defaulting to UTC now.
- [ ] **Step 4:** Run `uv run pytest -v`. Expected: the whole suite passes.
- [ ] **Step 5: Commit** `feat(web): session, attempt, reveal, report, mastery API`.

---

<!-- End preserved source. -->
