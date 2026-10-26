# C-R6: evaluation must distinguish usefulness, safety and selection

[Review](README.md) · [Protocol](../../superpowers/specs/2026-10-26-milestone-c/08-evaluation-protocol.md)

## Problems with the original contract

- A model can improve leakage by refusing every request; scoring only delivered hints hides
  the loss of coverage. Scoring only raw generations hides what the guard actually delivers.
- “10 points better on helpfulness OR leakage” allows a helpful model with worse leakage,
  or a silent model with no useful hints. Denominators differ across help types.
- An LLM judge scoring its own model family is not independent truth. A 20% spot-check of
  60 cases is only 12 cases and can miss rare failures or rubric disagreements.
- C says its final 24 cases run before LoRA, while the old plan reserves them for E. Once
  inspected during C, those cases are no longer an untouched final test for LoRA.
- Sixty prompts drawn from 22 bank problems are not 60 independent problem observations.
  Shared templates, repeated hint levels and related derivatives must remain in one split.
- Whole-book retrieval cannot be validated using only the three current derivative topics.

## Review amendments

Use separate raw-output and delivered-output metrics, an explicit applicable-case denominator,
useful-answer coverage and appropriate abstention. Count citation support semantically, not
merely successful chunk-ID resolution. Report blocked, retry, timeout and fallback rates.
Treat the 10-point threshold as a practical development selection rule, not a significance
test or formal non-inferiority result. Safety/coverage constraints must be fixed first.

Reserve a disjoint E/LoRA final partition; C's 24 are a frozen C release holdout, subsequently
a published regression set. Do not tune on the release holdout. If fixes use its failures,
label the rerun a regression and obtain fresh release cases for an independent claim.
Freeze final comparisons/arms in advance; “once” means one locked evaluation campaign,
not one model response ever. Reuse within that campaign is a paired comparison.

Keep the 20% blinded random human spot-check, stratified by help type/topic, and add all
flagged leakage, endorsement and judge disagreements. Report random-sample agreement
separately from targeted review. Audit math and citations against the actual source chunks.

## Remaining decision

The original acceptance table is a demo, not a quality gate. C-P2 must set minimum helpful
coverage, citation support and retrieval quality, maximum error/endorsement rates, and the
exact model-selection primary metric before the paid comparison. Zero observed leakage is
a sensible proposed release gate, but it is not a mathematical guarantee of no future leaks.
Always-abstain behavior must fail the useful-coverage gate.

Wilson intervals describe marginal proportions, not paired model differences or correlated
problem families. Add paired per-case outcomes and uncertainty grouped by problem family;
report small-sample limits instead of claiming superiority from a few points of difference.
