# Milestone C1 implementation review — brief (2026-10-27)

[Reviews](../README.md) · [Handoff](../../../handoff.md) · [C spec](../../superpowers/specs/2026-10-26-milestone-c/README.md) ·
[C1 plan](../../superpowers/plans/portfolio-mvp/milestone-c/c1/README.md)

**Status: brief only, no findings yet.** Reviewer: Codex (deep dive). Branch `milestone-c1`,
base `main` 292cee4, head = the commit that adds this file. About 146 files, +17k lines
(most of it `content/corpus/chunks.jsonl`; exclude it from diffs). Nothing deployed or merged.
Local evidence at head: pytest 1561 passed / 3 skipped; `npm test --prefix tools` 41/41.
No paid call, no container run, no holdout run has happened.

## What to judge

1. Does the code meet the [C spec](../../superpowers/specs/2026-10-26-milestone-c/README.md)
   as amended by the [concept review](../2026-10-26-milestone-c/README.md) (C-R1 to C-R7)?
2. Are the [execution rulings R1–R30](../../superpowers/plans/portfolio-mvp/milestone-c/c1/21-rulings.md)
   sound? Each one amends the plan; flag any that weakens the spec.
3. Is the release protocol honest: gates fixed before results, holdout one-shot, spend capped?

## Reading order and files

| Area | Files | Main questions |
|---|---|---|
| Parser | `src/mathtutor/help/latex_parse.py` | Allowlist complete? Any input that crashes, hangs or misparses into a false "safe"? |
| Leak guard | `help/leak_guard.py`, `help/render.py`, `tests/integration/test_guard_pool.py` | Fail-closed on every unchecked path? Renderer shows only guard-checked math (`split_spans`)? |
| Corpus | `tools/corpus/{fetch,build}.py`, `retrieval/{mathml,corpus}.py`, `content/corpus/` | Reproducible from the snapshot? Exercises/answer keys never retrievable (R15, R16)? |
| Retrieval | `retrieval/{bm25,query}.py` | Tokenizer `tok-2`, section boost, byte caps; any dev-tuning leak into the holdout (R29)? |
| State, money | `help/ledger.py`, `migrations/versions/0004_help.py`, `store/models.py` | Integer micro-USD; reservation → settle/uncertain; no overspend under concurrency? |
| Context, prompts | `help/context.py`, `help/prompts.py`, `help/prompts/v1/*.md`, `content/help/confusions.json` | Answer filter (R23); misconception notes error-only (R19); choice options hidden (R20)? |
| Generator | `help/generator.py`, `help/config.py`, `help/help_config.json` | `anthropic==2.3.0` usage, `max_retries=0`, structured output; refusal/truncation never shown? |
| Pipeline, service | `help/pipeline.py`, `help/service.py`, `application/practice.py` | Admission → commit → work → finalize; stale on submit; double click; privacy epoch on clear? |
| Web | `web/{api,app,schemas,security}.py`, `web/static/practice.js`, `templates/practice.html` | Per-user limits, `Retry-After`, no student text in logs, import boundary (no SymPy in web)? |
| Evaluation | `help/eval/*.py`, `evals/help/` | Gates mechanical and predeclared (`c1/02-gates.md`)? Wilson intervals right? Spend cap enforced? |
| Ops | `docs/ops/{runbook-c1,security,host-sizing-c1}.md`, `Dockerfile`, `deploy/` | Key handling, help-off switch, memory claims labeled preliminary? |

## Known limits (do not re-report unless you think the disposition is wrong)

- Dev Recall@6 is 0.79 against a 0.80 gate; a reviewer saw draft holdout BM25 Recall@6 0.576
  (disclosed in the status page). Thomas decides the gate before the holdout.
- The guard checks extracted math only; prose and cumulative leakage are measured, not prevented.
- `max_output_tokens` 1000 with adaptive thinking may truncate; truncation abstains, but the
  dev run should report the rate.
- `test_cot_irrational_removable_hole_is_proven` is a known SymPy timing flake (from B).
- Container smoke and container memory are not run (no Docker on the dev machine).
- Eval cases and retrieval labels are drafts until Thomas sets `reviewed_by: tg`.

## How to run

```
uv sync
uv run pytest -q
npm test --prefix tools
uv run python -m mathtutor.help.eval.run --split dev --retrieval-only --draft
uv run ruff check . && uv run mypy src
```

Do not set `MATHTUTOR_ANTHROPIC_API_KEY` or run paid commands; do not run the holdout split
(it writes a one-shot "started" marker).

## Output

Write findings in this folder as `01-…md` files (≤100 lines each) and a findings table here:
ID `C1-R<n>`, priority P1 (blocks release) / P2 (fix before C2) / P3 (note), file:line,
a reproduction or test name, and a proposed fix. Update `handoff.md` "Resume here" item 1.
