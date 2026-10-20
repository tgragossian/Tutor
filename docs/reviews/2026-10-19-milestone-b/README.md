# Milestone B documentation and evaluation review — 2026-10-19

[Reviews](../README.md) · [Handoff](../../../handoff.md) · [Execution status](../../superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md)

Reviewed local `milestone-b` 2ad5514 (implementation through a115846), focusing on task 8/9
evaluation, capture flow and task dependencies. Documentation only; no labels/code changed.
This is not a fresh exhaustive verifier-soundness audit or deployment check.

## Findings for Claude

### B-E1 — P1 before release: pending cases can satisfy a reviewed-dev gate

Location: [evaluate.py](../../../src/mathtutor/verify/evaluate.py), lines 96–101 and 268–293.
`Case._not_blank` accepts `pending`; `gate_failures` sees only aggregate metrics and counts.
All 131 committed draft cases load successfully with that reviewer. Once metrics improve,
`--set dev --gate B` can report success without the human review required by spec 08.
This is unfinished task 9 step 5, not evidence of an already-claimed reviewed release.

Fix: require an approved human reviewer on every release-dev row before gate success;
retain an explicit draft path. Test pending/generated/blank reviewers in human release mode.
Regenerate `dev.jsonl` after reviewing `dev.src.yaml`; never infer review from matching outputs.

### B-E2 — P2: absent negative cases and empty regressions pass gate B

Location: [evaluate.py](../../../src/mathtutor/verify/evaluate.py), lines 268–293.
The dev gate checks total count and correct-label coverage, but not negative-case presence.
An 80-case all-correct set yields FA 0/0 and passes. The generated gate also accepts zero rows:
no false accepts, errors or disagreements exist in an empty set.
Current committed sets are populated; this is a future regression/measurement guard gap.

Fix: reject empty generated sets without imposing the human 80-case minimum; require
human label/category coverage before release, using task 9's existing coverage table.
Category currently lives only in source YAML, so define how CI validates that provenance.
Add negative tests for empty and all-correct inputs; do not infer accuracy from FA 0/0.

### Existing draft questions needing decisions

- [translate.py](../../../src/mathtutor/verify/translate.py), lines 296–335:
  `d-log2-01` gets a positive-base restriction because the computed exponent lacks an exact
  rational value. Exact log₂8 = 3 should not lose negative-x coverage under R14.
  Bound computation before simplifying; abstain if exact classification cannot be established.
- [Review sheet](../../../evals/verifier/human/REVIEW.md): `d-181-05` is a display/parser
  ambiguity and label question. Thomas decides its treatment with a recorded rationale.
- Seven conservative domain abstentions remain; do not replace proof with sample agreement.
- Keep task 12 R12/R13 race and replay tests, task 13 kind checks, and task 14 error copy
  explicit. Those layers are still unimplemented and were reviewed only as plans.

## Reproductions and evidence

Read-only probe in the branch environment:

```python
from pathlib import Path
from mathtutor.verify.evaluate import Metrics, gate_failures, load_cases
m = Metrics(fa=(0, 0), fr=(0, 80), coverage=(80, 80), abstain={},
            by_kind_reason_method={}, agreement=(80, 80))
print(gate_failures(m, 80, "dev"))  # []
empty = Metrics(fa=(0, 0), fr=(0, 0), coverage=(0, 0), abstain={},
                by_kind_reason_method={})
print(gate_failures(empty, 0, "generated"))  # []
cases = load_cases(Path("evals/verifier/human/dev.jsonl"))
print(sum(c.reviewer == "pending" for c in cases))  # 131
```

- Fresh Windows suite: `uv run pytest -q` → **576 passed, 1 skipped, 1 warning**.
  Linux-only memory-limit test skipped; existing Starlette/httpx warning.
- [Committed draft](../../../evals/verifier/results/dev-draft.json): FA 0/54 (Wilson upper
  6.6%), FR 2/52, coverage 43/52, unsupported accepts 0/25, agreement 122/131,
  internal errors 0. This is unreviewed, fails B, and was not regenerated in this pass.
- B-C1/B-C2/B-C3 are resolved by recorded fixes; earlier failing-suite counts are historical.
- Markdown checker and `git diff --check` pass. All 146 maintained Markdown files are
  reachable from README/handoff and at most 100 lines; the generated pytest-cache README
  also passes the line check and is excluded from the maintained documentation tree.
- Docker, Linux containment, browser recapture, CI and the live host were not revalidated.
