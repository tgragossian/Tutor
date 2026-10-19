# R22/R23 Implementation Plan: function parentheses and domain rewrites

[Milestone B plan](../README.md) · [Spec](../../../../specs/2026-10-19-function-input-and-domain-rewrite-design.md) · [Rulings](../02-execution-rulings.md) · [Review sheet](../../../../../../evals/verifier/human/REVIEW.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** students must write `\sin(x)` (R22), and domain restrictions on trig denominators,
`e^u` and `|u|` are decided exactly on their inner argument (R23), before task 10.

**Architecture:** R23 adds a pure constraint-rewrite module that `equivalence._exact_violations`
calls before the existing R19 solvers. R22 adds a LaTeX rule to `precheck` (reject only),
the same rule to the content check for authored LaTeX, and recaptured dev cases.

**Tech Stack:** Python 3.12, SymPy, pytest, Node tools (MathLive 0.111.1, Compute Engine 0.151.0).

**Spec:** [2026-10-19 function input and domain rewrites](../../../../specs/2026-10-19-function-input-and-domain-rewrite-design.md).
Executors read the spec and this plan together; decision 0001 wins over both.

## Global Constraints

- Symbolic proof is required for `correct`; sampling may only refute (decision 0001).
- Never edit a dev-case label to match the verifier; edited or new cases stay `reviewer: 'pending'`.
- R22 reads LaTeX to **reject** only; grading uses MathJSON only.
- R22 function commands: `\sin \cos \tan \sec \csc \cot \ln \log \lg \lb \exp`.
- R22 copy (format issue `unsupported_notation`, detail): `Put the function's input in parentheses, like sin(x).`
- R22 accepted openers after a function and its `^`/`_` groups: `(`, `\left(`, and the
  absolute-value openers `|`, `\lvert`, `\vert`, `\left|`, `\left\lvert`, `\left\vert`.
- R23 rewrites are exact real equivalences; anything not reduced still raises `DomainUnproven`.
- Every Markdown file ≤ 100 lines, linked from its parent. No AI co-author trailers.
- Before each commit: `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src`, `node --test` in `tools/`, `uv run python tools/check_docs.py`.

## Review Focus

1. A misconception written `\sin x` is rejected by R22 and so "passes" the
   not-graded-correct check vacuously → Task 3 makes a rejected misconception a content error.
2. `\sin^2(x)`, `\log_{10}(x)`, `\sin^{-1}(x)`-style groups before the parenthesis must not
   trip the rule; `\sin\left(x\right)` must pass → Task 2 parametrized accepts.
3. Command prefixes: `\sinh`, `\cosh`, `\lnot`, `\left` must not match `\sin`/`\ln`/`\lb`
   → Task 2 test (word boundary on letters).
4. Escaped or spaced input: `\sin  (x)` and `\sin\,(x)` → Task 2 accepts after whitespace and
   thin spaces `\,` `\;` `\!` `\ `.
5. `cos(x) > 0` and `|x|^(1/2)` must still abstain after R23 → Task 1 negative tests.

## Tasks

| # | Task | Est. h |
|---|---|---:|
| 1 | [R23 constraint rewrite](01-domain-rewrite.md) | 1.5 |
| 2 | [R22 pre-check rule](02-precheck-rule.md) | 1 |
| 3 | [R22 authored content](03-content.md) | 1 |
| 4 | [Dev cases, recapture, rulings and docs](04-dev-cases-docs.md) | 1 |

Order 1 → 2 → 3 → 4. Task 4 needs 2 and 3; task 1 is independent. Thomas reviews the
recaptured cases with the rest of task 9.
