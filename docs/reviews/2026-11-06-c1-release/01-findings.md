# C1 release review findings (2026-11-06)

[Brief](README.md) · [Handoff](../../../handoff.md) · [Tuning](../../superpowers/plans/portfolio-mvp/milestone-c/c1/22-tuning.md)

## R1 — Latest-attempt prompt fix: code path correct, live validation pending

`assemble_context` keeps the newest attempt first for retrieval. `prompts._context_block`
reverses only its display list, labels the last row `LATEST attempt`, and the hint, feedback
and hint-choice tasks all refer to that label. The judge reads eval case attempts oldest
first, with the latest last; it does not rely on the generator's display order. The prompt
regression passes. No other active help prompt says "first one listed."

The one-shot holdout used prompt fingerprint `1ba6dc7937da`; R40 changed that prompt after
the run. The holdout is valid evidence for the released beta at its frozen version, not an
independent measurement of R40. The reported host still runs `8b35584`, before R40. A new,
disjoint holdout is needed for a fresh performance claim about the changed prompt. An
dev run 3 (`20261106-024324-dev`) is now recorded with prompt `da2eb7555541` and rubric
v2. It has judge labels only and misses usefulness (20/36), citation support (29/33), guard
false blocks (10/42) and retrieval Recall@6 (0.774); do not call it an audited result.

## R2 — Answer box: fix is coherent; browser proof still needed

`#answer-field[read-only]` now retains the full-size frame while locked, and
`setFieldReadOnly(false)` clears MathLive's lingering attribute. `renderAnswer` sets `field`
to null for choice items, while `lockAnswer` still handles their radios. The Node tests
exercise lock and unlock state, but use a plain object without MathLive attribute behavior;
they do not prove the visual fix. Verify once with real MathLive after deploying this commit.

## R3 — Release posture: beta with measured misses

The audited holdout passed observed leak, math, citation and abstention gates, but missed
useful coverage (12/20), guard false blocks (7/23) and retrieval Recall@6 (0.722 vs 0.80).
Host memory stayed below its rule on 1 GB, but the 20-help mixed burst produced 6/8 grading
`verifier_busy` replies. Keep these limitations attached to the beta; the tuning list owns
follow-up work. The C1 status page still has a pre-release heading and pending gate table,
so readers should use its dated release evidence and this handoff until that page is cleaned.

## Validation

Focused prompt/context/eval-set tests: 44 passed. Node suite: 49 passed. This review did
not run a live browser, provider call, container test or new holdout. No production code was
changed in this review.

## Resolution (Claude, 2026-11-06)

R1/R2: `20a2b80` deployed (host checkout and image). R2 verified on the live site with real
MathLive (Playwright, account `uicheck_*`): answer box 672 px wide before, during (locked,
`read-only` set) and after a wrong check. R3: status heading and gate table updated (`178c8e0`).
A fresh disjoint holdout for the R40 prompt stays on the tuning list.
