# Baseline ladder: Codex design review

[Design](../../superpowers/plans/2026-11-06-baseline-ladder/00-design.md) ·
[Tasks](../../superpowers/plans/2026-11-06-baseline-ladder/README.md)

The four-arm comparison is useful as a diagnostic. Revise the plan before paid runs:

| ID | Finding | Recommendation |
|---|---|---|
| L1 | The 42 dev cases tuned the full tutor; a favorable result on them cannot answer the broad product question independently. Some level-0 step-2 cases are regression-only under the new one-hint behavior. | Use dev for wiring, then a fresh, disjoint and predeclared comparison set for the claim. Report regression-only cases separately. |
| L2 | The pasted arm says to paste production instructions verbatim, yet production requires schema/citations and passages that this arm lacks. The planned free-text reply is a different prompt contract. | Specify and version the exact pasteable text, with no citation/JSON obligations; explain every departure from production wording. Keep its input within what a student can actually paste. |
| L3 | The current `judge_items` only parses structured JSON. The tasks mention free text, but must also define how raw text becomes a `JudgeItem`, audit key, delivered score, and recomputed score. | Add one record shape and acceptance tests through judge, audit CSV, recompute, and comparison output before any paid call. |
| L4 | The leak guard extracts bounded math; free-text Markdown and prose can evade extraction. A `would_block=False` result is not proof of safety. | Score delivered leaks with the judge/human audit; show guard results as separate diagnostic data, including `unknown`/unparseable cases. |
| L5 | Classifier cost applies to both tutor arms when estimating site cost; the draft adds it only to the full arm. The student subscription for plain/pasted changes who pays, not the model's token cost. | Show provider-generation cost for all four arms, and an estimated classifier add-on for both no-retrieval and full. Label estimates separately from measured spend. |

Decisions: give the pasted arm an explicit, usable level instruction; keep one Sonnet model
for the controlled comparison; use the fresh set for any claim; retain the dev runs as
diagnostics. No paid runs or implementation were performed in this review.
