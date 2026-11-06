# C1 tuning list (after the 2026-11-06 beta release)

[C1 status](20-status.md) · [C1 rulings](21-rulings.md) · [Expansion queue](../../05-expansion-queue.md)

Findings from the dev and holdout audits and from Thomas testing the live site. Each prompt
change becomes prompt v2: add the matching dev cases first, rerun dev (about $1), audit, then
release. Holdout cases are never edited in response; new cases go to dev or a fresh holdout.

## Prompt and help behavior

1. **Hint level 1 blends attempts and praises the wrong term** (Thomas, live, 2026-11-06).
   On 5x³ − x + 1, attempt 1 `15x^2+1` then attempt 2 `15x-1`: the hint praised "the power rule
   on the first term" (the term that was wrong: exponent) and asked about −x (right this time,
   wrong in attempt 1). "What did I do wrong?" on the same attempts was correct.
   Fixes: label the prompt's attempts "Latest attempt (help with this one)" and "Earlier
   attempts (context only)"; level 1 praises only a part that is fully correct in the latest
   attempt. New dev case: two attempts where the right and wrong terms swap.
2. **Feedback can point at the wrong term** (dev-02-r1): praised a copied −x, sent the student
   to the +1, and implied a constant contributes to the derivative.
3. **Explain sets up the student's own problem** (dev-17-r2): wrote out this problem's factors
   and a step list. Explain should teach on a different function and stop at the concept.
4. **How much "What did I do wrong?" reveals** (dev-04-r3): decide after more live testing.
5. **Quotient rule mnemonic:** allow "lo d-hi minus hi d-lo, over lo-lo" for the quotient-rule
   confusion, as an uncited memory aid.

## Evaluation

6. **Rubric v3 candidates:** an "over-helps (does the setup)" field separate from `useful`.
7. **Pairwise preferences** (A / B / tie) on cases with two responses; the right tool for
   the LoRA vs hosted comparison (A/B 2).
8. **TutorBench Calculus baseline** for the hosted model, before the LoRA experiment.

## Retrieval and guard

9. **Example pinning** for procedure queries (most current Recall@6 misses); see the
   [label review](../../../../../reviews/2026-11-05-c1-label-review/README.md).
10. **Guard false blocks on general formulas:** explanations with f(x), g(x) are blocked as
    too many foreign symbols (dev-37/38), and the generic power-of-a-function rule is blocked
    because substitution makes it equal the answer (dev-42).
11. **Mixed-load CPU contention:** 20 simultaneous hints push grading to `verifier_busy` on
    2 vCPU ([host sizing C1](../../../../../ops/host-sizing-c1.md)); first try
    `admission.concurrency` 2.

## Small cleanups

12. `contracts/examples/help-response-delivered.json` still shows the old citation label
    ("3.6 The Chain Rule"); it should read "Calculus Volume 1, §3.6".
13. **Duplicate-looking citations:** with section-only labels (S2-5), three passages from one
    section show as three identical "Calculus Volume 1, §3.3" rows (Thomas, live). Merge rows
    per section, or number them ("§3.3, passage 1"), keeping each passage's own link.
