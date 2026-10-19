# Verifier evaluation

[Documentation index](../../docs/README.md) · [Spec 08](../../docs/superpowers/specs/2026-10-13-portfolio-core/08-verifier-evaluation.md)

**2026-10-19:** 131 dev cases remain unreviewed (`reviewer: pending`). The
[draft result](results/dev-draft.json) fails B: FR 2/52, coverage 43/52; FA 0/54 (95% upper bound 6.6%).
CI runs generated cases only; human review and the dev CI step remain task 9 work.

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
`rationale`, `reviewer`, and for captured cases `raw_latex` or `raw_keys` (the authored input).
`answer` is `{"mathjson": ..., "latex": ...}` or `{"choice_id": "a"}`.
`label` is `correct`, `incorrect` or `unsupported`. Decimals are read as exact literals.

## Metrics and gates

- FA: incorrect-labelled cases graded correct, over incorrect-labelled cases.
- FR: correct-labelled cases graded incorrect, over correct-labelled cases.
- Coverage: correct-labelled cases graded correct, over correct-labelled cases.
- An `unsupported` case graded correct is a zero-tolerance gate of its own.
- An `unsupported` case answered with a format issue (notation, size, empty, incomplete) agrees.
- Rates carry 95% Wilson intervals; 0 of n is shown as an upper bound, never "0%".

Gate B on `dev`: at least 80 cases, FA 0, FR at most 2%, coverage at least 85%.
Both modes reject unsupported accepts and internal errors.
Gate B on `generated` also requires every label to agree; there is no 80-case minimum.
Current gaps: pending reviewers and empty generated sets are accepted; dev can pass without
negative cases. See the [review and proposed fixes](../../docs/reviews/2026-10-19-milestone-b/README.md).

## Commands

Human cases are authored in `human/dev.src.yaml` and captured by typing each into a real
MathLive field (`npm run capture:eval --prefix tools` rewrites `human/dev.jsonl`).

```
uv run python -m mathtutor.verify.mutate
uv run python -m mathtutor.verify.evaluate --set generated --gate B
uv run python -m mathtutor.verify.evaluate --set dev --gate B --out evals/verifier/results/dev.json
```

The dev command currently measures a draft; it does not certify human review.
After Thomas reviews the source YAML, recapture JSONL before running the release gate.
Set `MATHTUTOR_GIT_SHA` to the tested commit before publishing results.
The commands exit 1 when a gate fails and print which. Results JSON records the verifier
version, the set's SHA-256, the metrics and every case outcome.
