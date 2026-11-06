# 2026-11-05 C1 owner label review: Codex brief

[Reviews](../README.md) · [C1 status](../../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md) ·
[Eval README](../../../evals/help/README.md) · [Handoff](../../../handoff.md)

Branch `milestone-c1`, base `0216962`, changes uncommitted in the working tree until this
review passes. Thomas plans to send the project to a prospective employer within a day, so
the release path (C1 status steps 2 to 9) follows this review directly.

## What changed

Owner checklist step 1 is complete: every help case and retrieval query is `reviewed_by: tg`.

| File | Change |
|---|---|
| `evals/help/cases/holdout.jsonl` | hold-05 reviewed, content unchanged (24/24 holdout cases now reviewed) |
| `evals/help/retrieval/dev.jsonl` | all 28 reviewed; labels changed on rq-dev-09, 21, 23, 24, 28 |
| `evals/help/retrieval/holdout.jsonl` | rq-hold-05 gains a worked example under the new how-to rule |
| `evals/help/README.md` | labeling policy adds the how-to rule (line count unchanged at 100) |
| `docs/.../c1/20-status.md` | step 1 done; step 4 retrieval gate decided by Thomas |

Label changes (Thomas, reviewing passage text and the live OpenStax anchors):

| Query | Before | After | Reason |
|---|---|---|---|
| rq-dev-09 tangent slope as limit of secants | def2, 2.1-txt6, 2.1-txt8 | def2, **3.1-txt4**, 2.1-txt6 | txt8 is mostly velocity; 3.1-txt4 states the secant-to-tangent limit directly |
| rq-dev-21 derivative of sin⁻¹x | thm3, ex4 | + **3.7-thm1** | ex4 derives the result with the inverse function theorem |
| rq-dev-23 logarithmic differentiation steps | rule1 | + **3.9-ex8** | how-to rule |
| rq-dev-24 set up a related-rates problem | rule1 | + **4.1-ex2-p1** | how-to rule |
| rq-dev-28 u-substitution | thm1, rule1 | + **5.5-ex1** | how-to rule (3 chunks) |
| rq-hold-05 implicit differentiation | rule1 | + **3.8-ex1** | how-to rule |

**How-to rule:** a procedure query also gets the section's first worked example (first part
of a multi-part example). Scoped by Thomas to procedure queries only; a broader
"every concept query gets an example" rule (33 of 40 queries) is deferred to the queue.

## Retrieval gate (step 4, Thomas)

Keep the holdout Recall@6 gate at 0.80. Free dev check after the labels:
`--split dev --retrieval-only` gives **Recall@6 0.7738, MRR@6 0.6732, Hit@6 0.9643** (28 queries),
down from 0.79 because the new labels add relevant chunks. Disclose dev as near the gate;
report the one-shot holdout result plainly, pass or miss. Example pinning for procedure
queries (a retrieval change) is deferred to after release, so no retrieval code changed.

## Please check

1. **Holdout integrity.** rq-hold-05 was relabeled by rule without any holdout retrieval run
   (none has ever run; `--retrieval-only` refuses holdout). Confirm the change is allowed by
   the policy and the R4 claim/ledger rules, and that no holdout claim file exists yet.
2. **Rule applied evenly.** Are any other dev or holdout queries procedure queries that the
   how-to rule should cover (candidates: rq-dev-07, 17, 18; rq-hold-08)? Flag, don't edit.
3. **Label validity.** Each new chunk id exists in `content/corpus/chunks.jsonl`, sits in the
   query's home section or a justified other section, and each query has 1–3 chunks.
4. **Gate text.** Step 4 in the status page still cites 0.79; update the record to 0.7738
   with the reason above if you agree, and check the handoff and runbook say the same.
5. **Tests.** `uv run pytest -q tests/unit/help/test_eval_drafted_sets.py` passed (7/7);
   the full suite passed (1645, 3 skipped) at `0216962` with `MATHTUTOR_ANTHROPIC_API_KEY`
   unset. `test_settings_defaults` fails when that variable is set in the shell (environment
   leak, not a product bug); decide whether the test should clear it.
6. **Docs.** Markdown tree rule (≤100 lines per file), links resolve, US spelling.

Codex dispositions: [01-findings.md](01-findings.md). Resolve the recorded labeling-policy
question before freezing the sets; then Thomas commits them and moves to wording approvals
and the paid dev run.
