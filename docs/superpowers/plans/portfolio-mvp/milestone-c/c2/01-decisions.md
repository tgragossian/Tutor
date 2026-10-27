# C2 decisions for Thomas (Q1–Q8)

[C2 plan](README.md) · [C2 gates](02-gates.md)

Proposed by Claude on 2026-10-27. Each has a default the tasks implement; Thomas approves or
changes it before execution. "Cost" is what the default costs if it is wrong.

| # | Decision | Proposed default | Cost if wrong |
|---|---|---|---|
| Q1 | How much a question may disclose | The current hint level's rule, but at least level 2 (`QUESTION_MIN_LEVEL = 2`). Questions never advance the ladder. | At level 1 a typed "how do I start?" gets a next step a Hint would not give yet. |
| Q2 | Storing the question | Never stored. `payload_hash` covers it (replay/conflict); clearing history overwrites that hash on question rows with `CLEARED_HASH` (64 zeros). | No record of questions for later review; the eval cases are the only question data. |
| Q3 | Prompt versioning | Additive files in `prompts/v1/`: `question.md` (task) and `question_system.md` (appended to `system.md` for questions only). C1 prompt files unchanged. | If you prefer a clean `v2`, C1's evaluated prompt set changes and C1 evidence no longer covers it. |
| Q4 | Routing labels | `hint`, `feedback`, `explain`, set by the model on every valid reply (abstentions too), stored in `help_requests.use_case`; agreement with your label is reported, not gated. | Labels are model opinions; a bad label changes nothing for the student. |
| Q5 | Out-of-scope rule | Questions not about this problem abstain, including other calculus topics (spec 06: item-scoped). | Students asking "what is a limit?" mid-problem get an abstention. |
| Q6 | Availability | Same as Hint: active or exhausted items; behind `question.enabled` in `help_config.json` (default `true`). | None; one switch. |
| Q7 | Student-facing copy | Label "Ask about this problem"; placeholder "For example: why does the chain rule apply here?"; button "Ask"; counter "N/500"; error "Type a question (up to 500 characters)." Disclosure adds "and any question you type". | Copy edit. |
| Q8 | C2 eval budget | C2 cases need about $0.5–1.5 (Haiku help + Sonnet judge; worst case $2.30 for 34 cases: 2 × 1,300 µ$ help + 64,000 µ$ judge each). C1 may use most of the $5; top up before Task 7's paid run. | The run stops at the cap; nothing breaks. |

## Rulings already made in this plan

- R-C2-1: The question goes into the BM25 query through the parameter that carries the
  confusion label today (renamed `request_text`), capped at `question_max_bytes` (500).
- R-C2-2: Normalization: Unicode NFC, strip, CRLF → LF, at most 2 consecutive blank lines;
  reject C0/C1 control characters other than `\n` and `\t`. Length counts code points.
- R-C2-3: The `HelpOutput` schema for questions is a separate `QUESTION_OUTPUT_SCHEMA` with a
  required `use_case` enum; the other types keep `HELP_OUTPUT_SCHEMA` byte-for-byte.
- R-C2-4: The env=test `FixedHintGenerator` adds `"use_case": "hint"` when the request's
  schema is the question schema, so the browser e2e needs no script.
- R-C2-5: C2 eval cases live in `evals/help/c2/`; holdout problems are the C1 holdout problems,
  so dev prompt work never touches a holdout problem.
