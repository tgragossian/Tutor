# C1 release gates and selection rule (resolves C-P2)

[C1 plan](README.md) · [Evaluation protocol](../../../../specs/2026-10-26-milestone-c/08-evaluation-protocol.md)

Proposed by Claude on 2026-10-26 for Thomas's review. Fixed before any paid comparison;
encoded in `src/mathtutor/help/eval/gates.py` (Task 14) so a run reports pass/fail mechanically.

## Partitions

- Help cases: 60 → 36 development / 24 C release holdout, grouped by `problem_id` (one problem's
  cases never split). The holdout uses ≥ 7 of the 22 bank problems, covering all three topics.
- Retrieval queries: 40 → 28 development / 12 holdout, grouped by section.
- LoRA/E final set: not authored in C1. C-P4 creates it from problems/questions disjoint from
  all 60 cases before LoRA experimentation. C1 code must not read any `final` split.
- Case mix per split (dev / holdout): mistaken reasoning 8/5, nearly-right 4/3,
  "just tell me the answer" 6/4, easy level-1 trap 6/4, out-of-scope or no-evidence 6/4,
  ordinary 6/4. Help types: hint ≥ 40%, feedback ≥ 25%, explain ≥ 20% of each split.

## Primary measure and model selection (development split only)

- **Primary:** error-specific help rate on cases with a known wrong attempt or misconception.
- **Choose Sonnet 5.5 only if** its primary rate ≥ Haiku's + 10 percentage points **and** it
  passes every safety/coverage gate below on development **and** no gate measure is worse than
  Haiku's by more than 5 points. Otherwise Haiku 5.5. If neither passes, neither ships.
- Prompt changes during development are allowed; each run is recorded. The holdout runs once,
  after model and prompt are frozen.

## Holdout release gates (delivered responses; counts with Wilson 95% intervals)

| Measure | Gate |
|---|---|
| Expression leak delivered (guard-detectable) | 0 |
| Any leakage, human-judged incl. prose, all levels | ≤ 1 of 24 |
| Wrong-reasoning endorsement | 0 of the mistaken-reasoning cases |
| Math errors in delivered text | ≤ 1 |
| Citation support (each cited chunk supports the text) | ≥ 90% of substantive responses |
| Useful coverage on in-scope cases | ≥ 70% (an always-abstaining system fails) |
| Appropriate abstention on out-of-scope / no-evidence cases | ≥ 3 of 4 |
| Guard false blocks on in-scope cases | ≤ 15% (reported; above it, fix prompt/parser before release) |
| Retrieval Recall@6 on holdout queries | ≥ 0.80; MRR@6 reported |
| p95 latency / mean cost per request | ≤ 10 s / ≤ 3,000 µ$ (Haiku) |

## Judging

- Judge: `claude-sonnet-5-5`, versioned rubric `evals/help/rubric/v1.md`, model identity hidden,
  order randomized, case answers and cited chunk texts provided to the judge only.
- Thomas reviews a stratified random 20% (by help type and topic) plus every flagged leak,
  endorsement, math error and judge/heuristic disagreement. Agreement is reported separately
  from targeted adjudication; Thomas's label wins.
- A failed holdout gate converts those cases to regression evidence; after a fix, new holdout
  cases are needed for a fresh independent claim (spec 08).
