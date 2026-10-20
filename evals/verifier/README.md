# Verifier evaluation

[Documentation index](../../docs/README.md) · [Spec 08](../../docs/superpowers/specs/2026-10-13-portfolio-core/08-verifier-evaluation.md)

**2026-10-20:** all 136 source cases are reviewed (`tg`, 9b2e1f2): 49 correct,
50 incorrect, 37 unsupported. [R24](../../docs/superpowers/specs/2026-10-20-decimal-places-design.md)
is approved but not implemented. Captured `dev.jsonl` still has old labels and pending markers.
Follow the [R24 checklist](../../docs/superpowers/plans/portfolio-mvp/milestone-b/r24/README.md)
for implementation, content, recapture and the release gate; CI still runs generated cases only.

Historical post-R22/R23 draft: FA 0/54, FR 0/52, coverage 52/52, agreement 136/136.
The stored [draft result](results/dev-draft.json) is older (131 cases). Neither is an R24
release result. With 50 incorrect labels, FA 0 would imply a 95% upper bound about 7.1%;
only actual reviewed gate metrics may be published on the resume.

Offline measurement of the SymPy verifier. It must never grade a wrong answer correct.

## Sets

| Set | File | Gate mode |
|---|---|---|
| `dev` | `human/dev.jsonl` (hand-written, captured from MathLive; [review sheet](human/REVIEW.md)) | all milestone B gates |
| `generated` | `generated/mutations.jsonl` | no false/unsupported accepts or crashes; full label agreement |

The generated set is **regression-only**. It is built by `mathtutor.verify.mutate` from the
seed expression problems and is never cited as accuracy.

## Case record

One JSON object per line: `id`, `family`, `problem_id` or `inline_spec`, `answer`, `label`,
`rationale`, `reviewer`, `category` (dev only), and for captured cases `raw_latex` or
`raw_keys` (the authored input).
`answer` is `{"mathjson": ..., "latex": ...}` or `{"choice_id": "a"}`.
`label` is `correct`, `incorrect` or `unsupported`. Decimals are read as exact literals.

## Metrics and gates

- FA: incorrect-labelled cases graded correct, over incorrect-labelled cases.
- FR: correct-labelled cases graded incorrect, over correct-labelled cases.
- Coverage: correct-labelled cases graded correct, over correct-labelled cases.
- An `unsupported` case graded correct is a zero-tolerance gate of its own.
- An `unsupported` case answered with a recognized format issue agrees (notation, size, empty,
  incomplete; R24 must add `wrong_decimal_places` to this mapping).
- Rates carry 95% Wilson intervals; 0 of n is shown as an upper bound, never "0%".

Gate B on `dev`: at least 80 cases, FA 0, FR at most 2%, coverage at least 85%; every
label present; spec 08 category minimums met; every reviewer `tg` (B-E1, B-E2, bdb1710).
Both modes reject empty sets, FA 0 of 0, unsupported accepts and internal errors.
Gate B on `generated` also requires every label to agree; there is no 80-case minimum.

## Commands

Human cases are authored in `human/dev.src.yaml` and captured by typing each into a real
MathLive field (`npm run capture:eval --prefix tools` rewrites `human/dev.jsonl`).

```
uv run python -m mathtutor.verify.mutate
uv run python -m mathtutor.verify.evaluate --set generated --gate B
uv run python -m mathtutor.verify.evaluate --set dev --gate B --draft   # unreviewed measurement
uv run python -m mathtutor.verify.evaluate --set dev --gate B --out evals/verifier/results/dev-b.json
```

`--draft` skips only the reviewer check, prints DRAFT and records `"draft": true`; it is
never a release result.
After Thomas reviews the source YAML, recapture JSONL before running the release gate.
Set `MATHTUTOR_GIT_SHA` to the tested commit before publishing results.
The commands exit 1 when a gate fails and print which. Results JSON records the verifier
version, the set's SHA-256, the metrics and every case outcome.
