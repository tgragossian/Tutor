# Milestone C1 implementation review (2026-10-27)

[Reviews](../README.md) · [Handoff](../../../handoff.md) · [C spec](../../superpowers/specs/2026-10-26-milestone-c/README.md) ·
[C1 plan](../../superpowers/plans/portfolio-mvp/milestone-c/c1/README.md)

**Review complete; nine open findings, five P1 release blockers.** Reviewer: Codex.
Reviewed `milestone-c1` at `3be5808`, against `main` at `292cee4`. No fixes implemented here.
Fresh evidence: pytest 1561 passed / 3 skipped; Node 41 passed; lint, types, content and
verifier B gates passed. Separate adversarial probes reproduce the findings below.
No paid call, container run, deployment or actual holdout run was performed in this review.

## Findings and navigation

| ID | Priority | Finding | Detail |
|---|---|---|---|
| C1-R1 | P1 | Production image omits required confusion configuration | [Runtime](01-runtime-and-guard.md#c1-r1-p1-ship-the-help-configuration) |
| C1-R2 | P1 | Foreign composite expressions bypass answer verification | [Guard](01-runtime-and-guard.md#c1-r2-p1-do-not-pass-unchecked-foreign-expressions) |
| C1-R3 | P1 | Post-dispatch exceptions release paid-call reservations | [Accounting](02-accounting-and-retries.md#c1-r3-p1-preserve-cost-after-dispatch) |
| C1-R4 | P1 | A new commit permits reusing the same holdout | [Evaluation](03-evaluation-and-retrieval.md#c1-r4-p1-freeze-dataset-use-not-only-the-commit) |
| C1-R5 | P2 | Last guard call can deliver after the request deadline | [Runtime](01-runtime-and-guard.md#c1-r5-p2-enforce-the-deadline-after-worker-return) |
| C1-R6 | P2 | Feedback retrieves against the oldest retained wrong attempt | [Retrieval](03-evaluation-and-retrieval.md#c1-r6-p2-query-the-latest-wrong-attempt) |
| C1-R7 | P2 | No-retrieval baseline never calls the model | [Evaluation](03-evaluation-and-retrieval.md#c1-r7-p2-make-the-ablation-measure-a-generator) |
| C1-R8 | P2 | Retrying a lost help response creates another paid request | [UI](02-accounting-and-retries.md#c1-r8-p2-retain-the-id-for-an-ambiguous-help-request) |
| C1-R9 | P1 | Interrupted evaluation loses durable spend records | [Accounting](02-accounting-and-retries.md#c1-r9-p1-persist-evaluation-spend-before-and-during-calls) |

[Validation and Claude's fix checklist](04-validation-and-next-steps.md) owns rerun commands,
evidence limits and closure requirements. P1 blocks release; P2 should be fixed before C2.
**Update 2026-10-27:** Claude fixed all nine (`38c2de4`..`9bde1d9`); fixing commits, tests and
four deviations (D1–D4) are in [dispositions](05-dispositions.md). They stay **open until
Codex verifies** them; Codex updates this table's status after the rerun.

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
