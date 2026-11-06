# Answers Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store each student answer as one complete row (owner, attempt number, verdict and
mistake type), classify every wrong answer, and drive the hint ladder by mistakes made.

**Architecture:** Migration 0006 merges `submissions` + `attempt_results` into `answers`;
`store/answers.py` owns every answer query. Help reads one oldest-to-newest attempt list.
Migration 0007 moves the ladder onto `answers.mistake_type`; a background Haiku classifier
fills it after each wrong answer.

**Tech Stack:** Python 3.12, SQLAlchemy 2 / Alembic on SQLite, FastAPI, Anthropic SDK, pytest.

**Spec:** [00-design.md](00-design.md) (decisions D1–D12, Thomas 2026-11-05).

## Global Constraints

- Work in a worktree `.claude/worktrees/answers-table` on branch `answers-table`.
- Windows/OneDrive: `UV_LINK_MODE=copy`; explicit UTF-8; raw strings for LaTeX.
- Never relax false-accept or answer-containment gates; grading behavior is unchanged.
- Each migration upgrades and downgrades cleanly; `migrate` must exit 0.
- Student-facing copy uses American English.
- Development Markdown stays ≤ 100 lines (`tools/check_docs.py`).
- Commits: no assistant co-author trailers (README "How this was built" covers it).
- No deploy, no host commands, no paid API calls in tests (fakes only).
- Full check before each commit: `uv run ruff check . && uv run ruff format --check . &&
  uv run mypy src && uv run pytest -q`.

## Review Focus

1. Two requests grade answers on one item at once → distinct `attempt_no`; the loser is stale.
   Test in Task 1.
2. The classifier finishes after a classifying hint labeled the answer (or the reverse) →
   the first label stays. Tests in Tasks 3 and 4.
3. Help is off, no key, or the month budget is spent → no classify call, `mistake_type` NULL,
   grading unaffected. Test in Task 4.
4. Migrating a DB with orphan submissions (no result), unapplied results and NULL
   `reserved_revision` → copied as-is; only applied rows get `attempt_no`. Test in Task 1.
5. Twenty wrong answers at once on the 1 GB host → bounded queue; overflow leaves NULL and
   the hint labels it. Test in Task 4.

## Tasks

1. [Answers table](01-answers-table.md): model, migration 0006, `store/answers.py`, callers.
2. [One attempt order](02-attempt-order.md): oldest → newest with `attempt_no`.
3. [Ladder by mistakes](03-ladder.md): migration 0007, `answer_id`, five tries.
4. [Background classifier](04-classifier.md): Haiku labels, ledger, wiring, privacy copy.
5. [Finish](05-finish.md): docs, full CI, merge to `main` (no deploy).
