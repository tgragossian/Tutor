# Step-by-step work (parked design)

[Specs index](README.md) · [Open register C-O7](../plans/portfolio-mvp/milestone-c/03-open-decisions.md)
· [Expansion queue](../plans/portfolio-mvp/05-expansion-queue.md)

Status: **parked** (Thomas, 2026-10-28). Brainstormed and agreed in conversation, not a reviewed
spec and not approved for implementation. Build after the planned work: C (C1 release, C2 as
planned), then the LoRA experiment; position relative to D/E is set when the LoRA ends, like C-O4.
Neither the LoRA training data nor the OpenStax RAG corpus depends on this feature.
Before implementation: finish the design sections (checking/storage, C2 change, testing), write
the full spec, review it, then plan.

## Goal

Students may show their work as a chain of equal lines, then submit the final answer, and see
the first line where the work stops being equal to the derivative. Submitting only the final
answer stays exactly as today.

## Decided (Thomas, 2026-10-28)

- **Deterministic marks only.** The existing SymPy verifier marks each line; no model is
  involved. AI explanation of the broken line is a later follow-up (below).
- **Marks only on submit**, and that submission uses a try. Show ✓ up to and including the
  first ✗; lines after it are unmarked ("Fix the marked line first."). This keeps the step box
  from being a free answer oracle: one submission reveals no more than grading the answer.
- **Derivative notation is encouraged in steps**, e.g. `d/dx(x^2)·sin x + x^2·d/dx(sin x)`;
  each line is evaluated (derivatives taken) and compared with the reference derivative.
  Other problem types later get comparable notation (lim, ∫) through the same extension point.
- **The final answer may not contain `d/dx`** or any unevaluated derivative. It is a format
  rejection that uses no try: "Your final answer can't contain d/dx. Finish taking the
  derivative first."
- **Line chain layout:** the first line shows a fixed, uneditable `d/dx(<function>) =`; each
  added line starts with `=`. The fixed prefix is never checked (it is always true).

```
Show your work (optional)
  d/dx(5x³ − x + 1) = [ d/dx(5x³) − d/dx(x) + d/dx(1) ]   ✓
                    = [ 15x² − 1 + 1                   ]   ✗  check your work here
                    = [ 15x² − 1                       ]      (not marked)
  [+ Add line]   [insert d/dx( )]
Final answer   f′(x) = [ 15x² − 1 ]          [Submit]
```

## Proposed defaults (stated, not objected to; confirm in the full spec)

- Expression problems only (18 of 22); choice needs no steps; numeric needs a later rule for
  the switch from f′(x) to its value at a point.
- At most 20 lines. Each line is checked under its own budget after the final answer; a slow or
  unsupported line is "not checked" and never delays or changes the final verdict.
- Correct final answer with a broken step: the answer still counts; the ✗ still shows.
- Steps are stored with the submission (needed for history and the follow-ups).
- No partial credit; no other notations (`f'`, `dy/dx`) in the first version.

## New work this needs (not a UI-only change)

- **Spike:** capture what MathLive emits for `\frac{d}{dx}(...)` before designing the parser.
- **Verifier:** accept a bounded derivative head in step lines only, evaluate it, then compare;
  needs its own false-accept evaluation like the B verifier.
- **Content:** a reviewed `start` field (the function) on each expression problem, with a
  SymPy content check that d/dx(start) equals the stored answer. Thomas reviews the 18 entries.
- **Storage:** add-column migration for steps and per-line marks; UI for the line chain.

## Follow-ups and effect on C

- When steps ship, C2 questions should see the steps and the first broken line: a small
  question-prompt/context change, then a paid re-run of the C2 question evaluation.
- Step-aware "What did I do wrong?" reopens C2 Q3 (C1 prompts byte-identical) and needs a
  feedback re-evaluation. Do it after steps, as its own step.
