# Expansion queue — option B

[Active plan](README.md) · [Decisions](../../../decisions/0001-delivery-verifier-attribution.md)

Start after the deployed three-topic practice/RAG core passes its operations and
evaluation gates. Retain the original features; complete each stage before starting the next.
Estimate each expansion separately rather than promising it inside the initial 160 hours.

| Order | Feature | Gate before advancing |
|---|---|---|
| 1 | Diagnostic | Persisted assessment sequence, sufficient item coverage, hidden live verdicts, useful report |
| 2 | Exam conditions and recap | Closed-book/formula-sheet/open-notes behavior, reviewed recall/concept content, complete recap flow |
| 3 | All 15 topics | Reviewed coverage and supported answer formats per topic, verifier evaluation and UI flows |
| 4 | Extraction pipeline | Reproducible HTML ingestion, source/answer matching, review workflow and audited error rates |

LoRA moved out of this queue: it runs directly after milestone C
([decision 0005](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md) §6), with the same gate:
same-model before/after comparison, held-out calculus evaluation, costs and regressions reported.

## Diagnostic

Start on the existing topics. Provide enough unseen eligible items for the declared
assessment plan; do not rely on one problem per topic.
Specify report access and verdict visibility before an assessment is complete.

## Exam conditions and recap

Restore recall/concept items, warm-up and formula-sheet behavior here.
Keep original recall/application scoring goals with explicit assisted-attempt semantics.
Review content rather than filling quotas with weak or duplicate questions.

## All 15 topics

Retain limits, continuity, theorem applications, implicit differentiation and integration.
Introduce needed answer formats only alongside reviewed examples and verification gates.
Use the [exact polynomial implicit contract](../../../decisions/0001-delivery-verifier-attribution.md).
General implicit curves remain outside that checker's initial supported family.
Expand selection policies and content coverage together; sparse banks cannot support
meaningful diagnostics or adaptation merely because all topic names appear in a menu.

## Extraction pipeline and LoRA

Use the original extraction goals, keeping candidates separate from approved graded content.
A computed answer does not validate a transcribed statement; audit both.
After extraction is stable, follow the [fine-tuning experiment](04-release.md) with
separate problem/conversation splits and fixed retrieval/decoding.
Other recorded future ideas stay in the background roadmap; this queue orders the
named features without bringing every future course into the first release.
