# C1: textbook-grounded help — implementation plan

[Milestone C plan](../../03-rag.md) · [Open register](../03-open-decisions.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Students on bank problems get Claude-written Hint / What did I do wrong? / Explain this
help, grounded in whole-book OpenStax retrieval with validated citations, behind a fail-closed
SymPy leak guard, durable spend/rate limits and an evaluated release gate.

**Architecture:** An offline tool freezes the book and builds `chunks.jsonl`; the web process
loads it into a local BM25 index. `HelpService` admits a request (durable reservation), builds
server-owned context, retrieves, calls a provider-neutral `Generator`, validates JSON and
citations, runs the leak guard (pure-Python LaTeX parser → MathJSON → existing checker in a
separate one-worker pool) and finalizes only if the item is unchanged.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy/Alembic on SQLite, SymPy (workers only),
`anthropic` SDK, vanilla JS + MathLive, Node test runner, Playwright.

**Spec:** [C design spec](../../../../specs/2026-10-26-milestone-c/README.md) with review
amendments; [Codex review](../../../../../reviews/2026-10-26-milestone-c/README.md).

## Plan tree

- [Pinned values (C-P1)](01-pinned-values.md) and [release gates (C-P2)](02-gates.md): Thomas reviews these numbers.
- [Shared interfaces](03-interfaces.md): names and types every task uses.
- Tasks: [1–2 config, parser](10-foundation.md) · [3 guard](11-guard.md) ·
  [4–5 corpus](12-corpus.md) · [6 retrieval](13-retrieval.md) · [7–8 state, ledger](14-state.md) ·
  [9–10 context, generator](15-context-generator.md) · [11–12 service, API](16-service-api.md) ·
  [13 UI](17-ui.md) · [14 evaluation](18-evaluation.md) · [15 release](19-release.md) ·
  [status and owner checklist](20-status.md) · [execution rulings](21-rulings.md).

Order: 1 → 2 → 3; 4 → 5 → 6; 7 → 8; 9, 10; then 11 → 12 → 13; 14 after 11; 15 last.
Tasks 4 and 14 have owner steps (Thomas reviews cases and labels); the rest is code.

## Global constraints

- The web process never imports SymPy/mpmath or `mathtutor.verify.check` (see `verify/pool.py`).
- New runtime dependency: `anthropic` only, pinned exactly in `pyproject.toml`/`uv.lock`.
  BM25, the LaTeX parser and the HTML renderer are local code. Windows: `UV_LINK_MODE=copy`.
- No real provider call in CI or pytest; `ScriptedGenerator` drives every test and the e2e run.
- The verifier's grading behavior, gates and false-accept rules do not change.
- Money is integer micro-USD (`int`); never floats. Months are UTC calendar months `YYYY-MM`.
- Student-facing copy uses US spelling; fixed messages live in `help/messages.py` only.
- Request logs and errors never contain student text, model output, chunk text or the API key.
- Migrations add tables/columns only (SQLite `batch_alter_table`), like `0003`.
- Markdown files stay ≤100 lines; commits carry no assistant co-author trailer.
- Ruff (line 100), `ruff format`, `mypy src`, pytest, docs check and CI stay green per task.

## Review focus

1. **Model notation the parser rejects** (`\left( \right)`, `\cdot`, `2x\cos x`, `\dfrac`,
   `f'(x)=`): expect parse or a foreign-symbol pass, not a block. Test: Task 2 notation table.
2. **Double-click / two tabs** on Hint: same ID replays, different IDs serialize on the item,
   the ladder advances once. Test: Task 11 `test_concurrent_hints_advance_once`.
3. **Answer submitted while a hint is in flight:** the hint is discarded as `stale`, no ladder
   advance, usage still settled. Test: Task 11 `test_submit_during_help_is_stale`.
4. **Provider timeout after billing:** no resend; reservation stays `uncertain` and counts
   against the month. Test: Task 8 `test_uncertain_counts_until_reconciled`.
5. **Missing key or corpus at start:** app is ready, help buttons hidden, practice works.
   Test: Task 12 `test_readyz_ready_without_help`.
