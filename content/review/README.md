# Task 15 content review (Thomas)

[Content](../README.md) · [Task 15](../../docs/superpowers/plans/portfolio-mvp/milestone-b/tasks/15-content-e2e.md)

**Reviewed 2026-10-22:** Thomas approved all 16 (now `human_verified`; 22 servable, 7 + 7 + 8).
For 223 he checked that his simplified form, (x/7 + 7/x)^6 - (x^2+49)^6/(2401x^8), is
equivalent; SymPy and the real verifier both grade it correct.

The 16 drafts were 15 OpenStax exercises and 1 author-written choice item.

- [3.3 Differentiation rules](3-3.md): 107, 109, 113, 137, 145
- [3.5 Trigonometric functions](3-5.md): 185, 187, 191, 193, 209
- [3.6 The chain rule](3-6.md): 215, 217, 223, 229, 231, adapted sin(x²)

## What was checked before review

- Statements transcribed from the OpenStax pages; answers match the OpenStax answer key.
- Each answer re-derived with SymPy from the original function; every wrong answer differs.
- `content_check` passes on all 22 (answers translate, are defined on their domain, wrong
  answers grade as incorrect). Each problem grades in about 1 s through the real verifier.
- Wording added to some statements: tangent-line items ask for the right-hand side of
  `y = …`; 145 adds "Give an exact answer or round to 4 decimal places" (R24).

## For each problem, check

1. The statement matches the book (exercise number, function, what is asked).
2. The answer is correct and the domain is right (most are all reals; 113 and 223 exclude
   0; 229 excludes 5/2).
3. Each wrong answer is a mistake a student would really make.

## To approve

In each file under `content/problems/`, set `review.status: human_verified`,
`reviewer: 'tg'` and `date: '2026-10-2x'`; or tell Claude which ids passed and what to change.
Then: `npm run compile --prefix tools`, remove the `xfail` on `test_all_human_verified`, and
the container smoke's `"servable":6` becomes 22.
