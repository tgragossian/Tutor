# Milestone C design: textbook-grounded help

[Specs index](../README.md) · [Milestone C plan](../../plans/portfolio-mvp/03-rag.md)

Status: design agreed with Thomas on 2026-10-26; Codex concept review completed against
`8126fc3`. [Findings and dispositions](../../../reviews/2026-10-26-milestone-c/README.md).
Review amendments clarify implementation contracts; they are not runtime evidence or new
owner approvals. A task-by-task implementation plan is still needed. Governed by decisions
[0004](../../../decisions/0004-rag-source-models-and-evaluation.md) (Anthropic only, amended
2026-10-26) and [0005](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md).
The design session is complete; implementation prerequisites are in the
[open register](../../plans/portfolio-mvp/milestone-c/03-open-decisions.md).

## Goal

A student working a problem asks for help and gets a Claude-written response grounded in
OpenStax *Calculus Volume 1*, with a working citation, aiming to withhold the final answer.
The bounded guard catches supported expression leaks; prose/cumulative leaks remain measured
limitations. Reveal is the only intentional answer action; hints-only C3 has no reference guard.
Students can also ask their own questions and bring their own problems (typed, photo or PDF),
for example a practice test from their teacher. Help covers the whole book, not only the
three derivative sections in the current bank.

## Scope agreed on 2026-10-26 (Thomas)

- Generator: Claude Haiku 5.5 by default; Sonnet 5.5 only if it wins by the fixed margin.
- Three buttons (Hint, What did I do wrong?, Explain this) plus a free-text question box.
- Retrieval corpus: the whole book, built by script. BM25 first.
- Citations use our own chunk IDs (option A), so Claude and the later Qwen LoRA share one
  output contract and are compared fairly. Anthropic's built-in citations are not used.
- Bring-your-own problems are an option beside the bank, including photo/PDF upload in C.
- Lightsail may move to 2 GB if measured memory needs it.

## Slices (each ships on its own, all before the LoRA)

| Slice | Ships |
|---|---|
| C1 | Whole-book corpus and BM25, three buttons on bank problems, citations, leak guard, limits, evaluation |
| C2 | Free-text question box with logged routing label |
| C3 | Own problems: typed or uploaded, student confirms, SymPy solves or the problem is hints-only |

Estimate: C1 alone matches the old 40-hour budget; all of C is about 70–90 hours.

## Sections

1. [Components](01-components.md): modules, Generator interface, memory.
2. [Help flow](02-help-flow.md): request, server context, help types, output schema.
3. [Leak guard, failures and limits](03-guard-and-limits.md).
4. [Own problems (C3)](04-own-problems.md): intake, confirm, solve, privacy.
5. [Evaluation and acceptance](05-evaluation-and-acceptance.md): cases, scoring, tests, done-when.
6. [State and accounting](06-state-and-accounting.md): retries, revisions, deletion, durable spend.
7. [Corpus contract](07-corpus-contract.md): reproducible builds, math preservation, citations.
8. [Evaluation protocol](08-evaluation-protocol.md): splits, coverage, selection and judging.
9. [Provider evidence](09-provider-evidence.md): verified public capabilities and execution checks.

## After C

Accepted order remains **C → Qwen LoRA → D/E → expansion** (decision 0005).
Automated all-of-Calc-1 graded sets need templates/drafts, review and a broader checker;
C-O4 owns their placement. Do not put this project ahead of LoRA by implication.
Exam/quiz workflows remain in the expansion queue; uploading a sheet in C3 is problem intake,
not timed-test orchestration or broader automatic grading.
