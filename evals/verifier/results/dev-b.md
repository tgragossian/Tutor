# Milestone B verifier results (reviewed dev set)

[Results](README.md) · [Verifier docs](../../../docs/verifier/README.md)

Source: [dev-b.json](dev-b.json), `evaluate --set dev --gate B`, verifier `0.1.0+b5ad4b2`,
content `fbb7917d6658`, committed in e995438 (2026-10-20). 136 cases, all reviewed by Thomas
(`tg`). This is a **development set**, not a held-out evaluation.

## Gate metrics (95% Wilson intervals)

| Measure | Observed | Denominator | 95% interval |
|---|---|---|---|
| False accepts (incorrect graded correct) | 0 | 50 incorrect | 0.0%–7.1% |
| False rejects (correct graded incorrect) | 0 | 49 correct | 0.0%–7.3% |
| Coverage (correct answers proven) | 49 | 49 correct | 92.7%–100% |
| Unsupported graded correct | 0 | 37 unsupported | 0.0%–9.4% |
| Agreement with the label | 136 | 136 | 97.3%–100% |
| Abstentions on correct / incorrect | 0 / 0 | 49 / 50 | 0.0%–7.3% / 0.0%–7.1% |
| Internal errors | 0 | 136 | — |

## By kind × reason × method

| Kind | Reason | Method | Cases |
|---|---|---|---|
| expression | proven | symbolic | 42 |
| expression | counterexample | refutation | 36 |
| expression | student_undefined | refutation | 1 |
| expression | undefined_on_domain | domain | 2 |
| expression | format: unsupported_notation | none | 12 |
| expression | format: incomplete | none | 5 |
| expression | format: input_too_large | none | 3 |
| numeric | proven | symbolic | 5 |
| numeric | counterexample | refutation | 6 |
| numeric | rounded_match | rounding | 1 |
| numeric | rounded_mismatch | rounding | 2 |
| numeric | format: wrong_decimal_places | none | 7 |
| numeric | format: unsupported_notation | none | 4 |
| numeric | format: input_too_large | none | 4 |
| numeric | format: empty / incomplete | none | 1 / 1 |
| choice | choice_match / choice_mismatch | exact | 1 / 3 |

Format replies are not verdicts: the student sees a message and keeps the try.

## Latency (reported, not gated)

Worker time per case from `dev-b.json` (single worker, the development machine that
produced the result, not the server):

| Cases | p50 | p95 | max |
|---|---|---|---|
| 99 graded (method not `none`) | 30 ms | 141 ms | 328 ms |
| all 136 (format replies return at once) | 0 ms | 125 ms | 328 ms |

The server's numbers (worker and queue time under a 16-user burst) are recorded in
[host.md](../../../docs/ops/host.md) after the task 16 load test.
