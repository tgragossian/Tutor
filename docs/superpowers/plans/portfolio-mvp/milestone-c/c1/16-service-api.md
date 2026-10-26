# C1 tasks 11–12: HelpService and the API

[C1 plan](README.md) · Previous: [context, generator](15-context-generator.md) · Next: [UI](17-ui.md)

### Task 11: HelpService orchestration

**Files:** Create `src/mathtutor/help/service.py`, `help/render.py`; Test
`tests/unit/help/test_service.py`, `tests/unit/help/test_render.py`, `tests/integration/test_help_races.py`.

**Interfaces:** Consumes everything in 03. Produces `HelpService`, `HelpIn`, `HelpOutcome`,
`HelpStatus`, `SourceRef`, `render_help_html(text: str) -> str`,
`HelpAvailability(enabled: bool, types: list[HelpType], confusions: list[Confusion], hint_level: int)`.

Flow (spec 06 steps 1–7): validate → in one `write_transaction`: ownership, revision, state ∈
{active, exhausted}, feedback needs latest consumed verdict `incorrect`, payload hash vs existing
`request_id` (same → replay/pending; different → `Conflict` 409), `ItemHelpState.in_flight` empty
(else return `PENDING` for the in-flight id), `Ledger.admit`, insert row `pending`, set
`in_flight` → commit → context, retrieval (drop any hit whose whitespace-stripped text contains
the stripped answer LaTeX or correct choice LaTeX; no hits → `ABSTAINED` without a provider call),
prompt, call 1 → validate schema + citations (all IDs in this request's hits) → guard → on
invalid/block, if a call remains: `reserve_call` + call 2 with `strict=True` → still bad:
`FALLBACK` (nudge for the top hit's section) → finalize in one transaction: recheck ownership,
revision, `privacy_epoch`, `help_seq`; stale → `STALE` with no text stored; else store output,
`help_seq += 1`, `hint_level += 1` (cap 3) only for a delivered `hint`; clear `in_flight`.
Any `GeneratorError` → `UNAVAILABLE` (`timeout` with `billed_unknown` → `mark_uncertain`, no resend).
Global `threading.BoundedSemaphore(4)`; not acquired → `UNAVAILABLE`. Deadline is checked
before every step; child timeouts get the remainder.

`render_help_html`: escape everything; blank line → `<p>`; `**x**` → `<strong>`; math spans →
`<math-field read-only>{escaped latex}</math-field>`; no links, images or raw HTML.

- [ ] **Step 1: Failing tests** (`ScriptedGenerator`, `FakePool`, real SQLite, fake clock):
  - `test_delivered_hint_with_citation`, `test_level_ladder_1_2_3_then_stays_3`,
    `test_feedback_requires_wrong_attempt`, `test_explain_requires_known_confusion`.
  - `test_unknown_citation_repairs_then_fallback`, `test_leak_repairs_then_fallback`,
    `test_refusal_counts_as_invalid`, `test_at_most_two_calls` (the script holds 3 bad outputs).
  - `test_timeout_marks_uncertain_no_resend`, `test_no_hits_abstains_without_call`.
  - `test_same_id_replays`, `test_same_id_different_payload_conflicts`.
  - `test_concurrent_hints_advance_once`: two threads, different IDs, same item → one
    `DELIVERED`, one `PENDING`; `hint_level` advanced once.
  - `test_submit_during_help_is_stale`: the scripted generator calls `PracticeService.submit_answer`
    before returning → `STALE`, no `output_json`, ledger settled, ladder unchanged.
  - `test_clear_history_during_help_stores_nothing`: epoch bumped mid-call → `STALE`, no text.
  - `test_help_never_changes_tries_or_revision`, `test_hit_containing_answer_dropped`.
  - `test_render_escapes`: `<script>`, `[x](http://a)`, `![i](u)` render as text; `$x^2$` → math-field.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(help): help service with guarded, race-safe finalization`.

### Task 12: API, availability, clear history and app wiring

**Files:** Modify `src/mathtutor/web/api.py`, `web/schemas.py`, `web/app.py`,
`application/practice.py` (`clear_history` hook), `contracts/` (add `help.request.json`,
`help.response.json`, examples); Test `tests/integration/test_help_api.py`, extend `test_api_contracts.py`.

**Interfaces:** `POST /api/help` (CSRF) body `HelpIn` → `200 HelpOutcome` for terminal statuses,
`202` for `PENDING`, `409` stale revision or conflicting ID, `429 help_limited`. `PublicItem`
gains `help: HelpAvailability | None`. Help is enabled iff `help_generator != "off"`, the corpus
loads with a valid hash, and (for `claude`) a key is set; otherwise `help` is `null` and the
endpoint returns `UNAVAILABLE`. `clear_history` additionally nulls `output_json`, sets `cleared_at`
on the user's help rows and increments `privacy_epoch`, in the same transaction. `_reserve` in
`practice.py` sets `next_submission_id` on the item's latest delivered help row whose
`finished_at` precedes the reservation and whose `next_submission_id` is null (follow-up link).

- [ ] **Step 1: Failing tests:** `test_help_requires_csrf_and_owner` (other user's item → 404),
  `test_readyz_ready_without_help` (no key → `/readyz` 200, `help` null),
  `test_clear_history_removes_help_text_keeps_usage`, `test_question_type_rejected_in_c1` (422),
  `test_contract_examples_validate`, `test_logs_have_no_student_or_model_text` (caplog),
  `test_next_attempt_linked_once` (two submits after one hint → only the first is linked).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Full `uv run pytest -q` → PASS.
- [ ] **Step 5:** Commit `feat(web): help endpoint, availability and history clearing`.
