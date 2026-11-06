# C1 recheck: remaining evaluation defects

[Recheck](07-recheck.md) · [Runner](../../../src/mathtutor/help/eval/run.py) · [Probes](test_recheck_probes.py)

Pre-fix evidence: 2026-10-28, `b16a206`. Both defects are now [fixed locally](11-debugging-fixes.md).
The descriptions below preserve the reproduced failures; saved probes now pass without xfails.

## C1-R4 — reopened P1: retrieval bypasses the partition boundary

`_execute` computes and prints retrieval metrics before calling `holdout.claim`.
Its `retrieval_only` branch returns immediately after printing. `check_freeze` checks
commit cleanliness and unclaimed legacy markers, but does not reject overlapping claimed
partitions. Thus a claimed holdout can still reveal retrieval results on another commit;
an unused retrieval-only holdout is also not recorded as consumed.

`test_used_holdout_cannot_be_scored_by_retrieval_only` creates a temporary claim, mocks
the current commit and loaders, and expects `RunnerError`. It instead prints retrieval
metrics and returns 0. No real holdout label, result or claim was read or written.

Fix: put every holdout result-producing path behind the partition-use boundary before
computing or printing metrics. Either refuse retrieval-only holdout runs or atomically
claim them as part of the locked campaign. A rejected paid rerun must not print scores
before rejection. Do not restore a per-commit exception or silently erase old claims.

Acceptance tests must cover already claimed and unused partitions, retrieval-only and paid
paths, concurrent starts, and no metric output on rejection. Use synthetic partitions.
Keep the existing overlap/legacy-marker tests: they verify useful parts of D2/R32.

## C1-R7 — reopened P2: baseline disappears before judging

[judge_items](../../../src/mathtutor/help/eval/judge.py) parses raw responses only as
`HelpOutput` or `HintChoiceOutput`, both requiring citations on non-abstaining output.
The no-passage pipeline correctly accepts `UncitedHelpOutput`, whose source list must be
empty. Its delivered output therefore disappears from judge items and the audit derived
from them; calling the generator alone does not make the comparison evaluable.

`test_no_passage_generation_reaches_judge_and_audit` delivers an uncited scripted hint.
The outcome is `delivered`, but `judge_items` returns `[]`, `judge_case` returns
`no_items`, and no judge request is made.

Fix: retain the response's evaluation mode/schema and ingest uncited baseline output in
the judge/audit path without relaxing production citation validation. Account for R35's
classifying hint output too. Citation support stays not applicable for the baseline;
usefulness, leakage, mathematical correctness and wrong-answer endorsement still count.

Acceptance: a synthetic baseline response reaches a blinded judge and an audit row; human
labels survive recompute and affect paired metrics. Cover ordinary and classifying hints,
blocked raw output, malformed output, and a production reply with missing citations.
Remove `--no-judge` from the documented quality-comparison example once this path works;
retain it only for explicitly labeled generation/cost diagnostics.
