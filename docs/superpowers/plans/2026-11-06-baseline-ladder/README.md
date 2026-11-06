# Baseline Ladder Plan (draft: awaiting Codex review)

[Plans](../README.md) · [Handoff](../../../../handoff.md) · [Help evaluation](../../../../evals/help/README.md)

> **Status:** draft. Do not implement until Codex has reviewed it (findings in
> `docs/reviews/<date>-baseline-ladder/`) and Thomas has approved it and the spend.
> For agentic workers, after approval: REQUIRED SUB-SKILL superpowers:subagent-driven-development.

**Goal:** answer "is any of this needed?" with one table: a plain request, a paste-in prompt,
the tutor without the textbook and the full tutor, on the same 42 dev cases, with leaks,
usefulness, accuracy, latency and cost per useful hint.

**Architecture:** two new evaluation-only arms in `mathtutor.help.eval.run` (`--arm plain`,
`--arm pasted`) next to the existing full and `--no-retrieval` runs. The two new arms deliver
the model's raw text, run the leak guard in measure-only mode, and reach the same judge,
audit and recompute path. Production code paths are unchanged.

**Spec:** [00-design.md](00-design.md) (Thomas 2026-11-06).

## Global Constraints

- Evaluation-only: nothing under `web/`, `application/` or the production `HelpPipeline`
  behavior changes; production never selects a new arm.
- Same model for every arm (Claude Sonnet 5.5), same judge, same rubric (v2), same cases.
- No network in tests; paid runs only by Thomas with `--max-usd`.
- Results are dev-set results; reports say so and give 95% intervals.
- Docs ≤ 100 lines; no assistant co-author trailers; American English.

## Review Focus

1. A plain-arm reply that contains the answer is counted as a delivered leak, never filtered.
2. Arms whose output is free text still reach judge, audit and recompute.
3. The guard's would-block decisions are recorded but never change delivered text in new arms.
4. Cost per useful hint uses the same denominator rules in every arm.
5. Old run directories (no `arm` in metadata) still load and report as before.

## Tasks

1. [Arms in the runner](01-arms.md): `--arm`, prompts, measure-only guard, free-text records.
2. [Cost and compute columns](02-costs.md): cost per useful hint, guard time, classifier cost.
3. [Runs and report](03-runs.md): Thomas's paid runs, audit, comparison table, README.
