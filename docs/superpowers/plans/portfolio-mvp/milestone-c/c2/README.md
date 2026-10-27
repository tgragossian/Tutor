# C2: item-scoped questions — implementation plan

[Milestone C plan](../../03-rag.md) · [C1 plan](../c1/README.md) · [Open register](../03-open-decisions.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On an open bank item, a student types a question (≤ 500 characters) and gets a
textbook-grounded, cited, leak-guarded answer about that problem; requests for the answer are
blocked or redirected, and a descriptive routing label (hint / feedback / explain) is logged.

**Architecture:** `question` becomes a fourth help type on the C1 path. The question text
joins the BM25 query and the prompt (inside `<student_text>`), the model returns the C1 output
plus `use_case`, and everything else (admission, ledger, guard, repair, finalize) is C1 code.
The question is never stored; only the routing label and a hash are.

**Tech Stack:** as C1: Python 3.12, FastAPI, SQLAlchemy/Alembic on SQLite, `anthropic`
(structured outputs), vanilla JS, Node test runner, Playwright.

**Spec:** [C design spec](../../../../specs/2026-10-26-milestone-c/README.md), mainly
[help flow](../../../../specs/2026-10-26-milestone-c/02-help-flow.md),
[guard and limits](../../../../specs/2026-10-26-milestone-c/03-guard-and-limits.md),
[state](../../../../specs/2026-10-26-milestone-c/06-state-and-accounting.md) and
[acceptance](../../../../specs/2026-10-26-milestone-c/05-evaluation-and-acceptance.md) (C2 row).

## Plan tree

- [Decisions for Thomas (Q1–Q8)](01-decisions.md) and [C2 gates](02-gates.md): review first.
- Tasks: [1–2 foundation, pipeline](10-foundation-pipeline.md) ·
  [3–4 service, API](11-service-api.md) · [5 UI](12-ui.md) ·
  [6–7 evaluation](13-evaluation.md) · [8 release](14-release.md).

Order: 1 → 2 → 3 → 4 → 5; 6 after 2; 7 after 6; 8 last. Branch `milestone-c2` is rebased on
`milestone-c1` `fb0ccd5` (C1 review fixes); rebase onto `main` once C1 merges. Do not start
Task 1 until Codex has closed the C1 review. Owner steps: Q1–Q8, case review, paid runs.

## C1 fixes this plan builds on (review C1-R1..R9)

- Guard (R2, R5): foreign shapes and `f(x)` are substituted atoms, every variant checked; a
  clearance after the deadline blocks. Questions get both for free; Task 2 adds no guard code.
- Accounting (R3): every call is recorded as `dispatched` before it is sent, so a crash
  keeps its cost uncertain. Question calls use the same pipeline loop, unchanged.
- Query (R6): `ctx.attempts` is newest first; feedback uses the latest wrong attempt.
- Baseline (R7): `HelpPipeline(..., no_passages=True)` and `build_prompt(..., no_passages=)`
  exist for `--no-retrieval`; the question suite refuses `--no-retrieval` (Task 6).
- Browser retry (R8): `helpUnresolved` keys unanswered requests; Task 5 adds the question
  text to the key so an edited question is a new request.
- Evaluation (R4, R9): `eval/spend.py` journals every call; `eval/holdout.py` claims a
  holdout's ids. Task 6 reuses both; claims gain a `suite` so C2 cases may use C1's holdout
  problems (R-C2-6).

## Global constraints

- Everything in the [C1 global constraints](../c1/README.md#global-constraints) still holds
  (no SymPy in web, `anthropic` only, scripted generator in CI, integer micro-USD, US spelling,
  fixed messages in `help/messages.py`, ≤100-line Markdown, no assistant co-author trailer).
- Question text: 1–500 characters after normalization (spec 02). Never logged, never stored
  in the database, never sent anywhere but the prompt and the BM25 query.
- C2 stays item-scoped: no conversation history, no earlier questions in the prompt, no
  independent chat (spec 06). Every question carries the current item's server-owned context.
- Routing labels are descriptive only: they never pick a different guard, prompt path, limit
  or ladder rule (spec 02). Questions never advance the hint ladder (spec 06 step 6).
- C1 prompts `system.md`, `hint.md`, `feedback.md`, `explain.md` stay byte-identical, so C1's
  evaluation evidence still applies to those types (Q3).
- Questions share C1's per-user, per-item and monthly limits; no new budget.
- Migrations add columns only (`0005`), like `0003`/`0004`.

## Review focus

1. **"Just tell me the answer" / "is it 2x?"**: no leak, no confirmation; reply is a hint,
   an abstention or the fallback. Test: Task 2 `test_question_confirming_guess_is_blocked`.
2. **Prompt injection in the question** ("ignore your rules", a fake `</student_text>`):
   stays data. Test: Task 2 `test_question_tags_neutralized`.
3. **Question while a hint is in flight / submit during a question**: same C1 serialization
   and stale rules. Test: Task 3 `test_question_and_hint_serialize_on_item`.
4. **Clear history right after asking**: no question-derived data survives (hash replaced).
   Test: Task 3 `test_clear_history_scrubs_question_hash`.
5. **Emoji, RTL text, 500 vs 501 characters, only whitespace, control bytes**: counted as
   characters, rejected with a clear message. Test: Task 1 `test_normalize_question_bounds`.
