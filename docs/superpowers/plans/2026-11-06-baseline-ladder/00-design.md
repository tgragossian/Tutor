# Baseline ladder: design (Thomas, 2026-11-06)

[Plan](README.md)

## Question

Thomas's "ChatGPT test": if a student asks a chatbot for a hint with nothing else and the
help is fine, none of this system is needed; if a good prompt is enough, students could paste
it; if the textbook is also needed, that is the interesting result. The fine-tuned model is the
later real test; this table becomes its baseline.

## Arms (each adds one piece)

| Arm | Model input | Guard | Ladder | Textbook |
|---|---|---|---|---|
| 1 `plain` | No system prompt. User message: problem, the student's attempts, and a natural request per help type ("Can you give me a hint?", "What did I do wrong?", "Can you explain …?") | measure only | none | no |
| 2 `pasted` | The production system prompt and help-type instructions, verbatim, pasted as the user's own message, plus problem and attempts; uncited free-text reply | measure only | case's labeled level, written into the pasted text | no |
| 3a `--no-retrieval` | Existing baseline (`no_passages.md` addendum) | on | server | no |
| 3 full | Existing production path | on | server | yes |

Arm 1 vs 2: what the prompt buys. 2 vs 3a: what the guard, structured output and server
control buy. 3a vs 3: what the textbook buys.

## Fairness rules

- Score what the student would see: in arms 1–2 the raw reply is delivered; a leak counts.
- Report leaks per case and per delivered response; usefulness over all in-scope cases, so
  abstaining cannot look safer; math errors over delivered responses.
- Report the answer-seeking category as its own row.
- Arm 3 also reports what the guard blocked (how much safety the guard, not the prompt, did).
- One model (Sonnet 5.5) for all arms: the claim is about the system, not the vendor.

## Cost and compute

Per arm: mean and total USD, **cost per useful hint**, calls per case, p50/p95 latency,
guard CPU ms per response. Arm 3 adds the background classifier's Haiku call for each wrong
answer. Write-up states who pays: arms 1–2 run on the student's own subscription; arm 3 is
paid per hint by the site.

## Caveats (stated in every report)

Dev cases were used to tune the full tutor; single-turn only (real students can push back);
small n (95% intervals); human audit is not blind to arm (the judge is, within a run).

## Open questions for Codex

1. Should arm 2 get the case's labeled level (generous to arm 2) or one generic instruction?
2. Is the leak guard's extraction valid on free-text replies (Markdown `$…$` math)?
3. Should arm 1 also run on Haiku to show the cheapest plain option?
4. Is reusing the dev set acceptable, or should a small fresh set be drafted first?
