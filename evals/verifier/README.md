# Verifier evaluation

[Documentation index](../../docs/README.md) · [Spec 08](../../docs/superpowers/specs/2026-10-13-portfolio-core/08-verifier-evaluation.md)

Offline measurement of the SymPy verifier. It must never grade a wrong answer correct.

## Sets

| Set | File | Gate mode |
|---|---|---|
| `dev` | `dev.jsonl` (hand-written, reviewed; added in task 9) | all milestone B gates |
| `generated` | `generated/mutations.jsonl` | zero false accepts only |

The generated set is **regression-only**. It is built by `mathtutor.verify.mutate` from the
seed expression problems and is never cited as accuracy.

## Case record

One JSON object per line: `id`, `family`, `problem_id` or `inline_spec`, `answer`, `label`,
`rationale`, `reviewer`. `answer` is `{"mathjson": ..., "latex": ...}` or `{"choice_id": "a"}`.
`label` is `correct`, `incorrect` or `unsupported`. Decimals are read as exact literals.

## Metrics and gates

- FA: incorrect-labelled cases graded correct, over incorrect-labelled cases.
- FR: correct-labelled cases graded incorrect, over correct-labelled cases.
- Coverage: correct-labelled cases graded correct, over correct-labelled cases.
- An `unsupported` case graded correct is a zero-tolerance gate of its own.
- An `unsupported` case answered with a format issue counts as agreement.
- Rates carry 95% Wilson intervals; 0 of n is shown as an upper bound, never "0%".

Gate B on `dev`: at least 80 cases, FA 0, FR at most 2%, coverage at least 85%.
Gate B on `generated`: FA 0 and no unsupported accepts; there is no minimum case count.

## Commands

```
uv run python -m mathtutor.verify.mutate
uv run python -m mathtutor.verify.evaluate --set generated --gate B
uv run python -m mathtutor.verify.evaluate --set dev --gate B --out evals/verifier/results/dev.json
```

The commands exit 1 when a gate fails and print which. Results JSON records the verifier
version, the set's SHA-256, the metrics and every case outcome.
