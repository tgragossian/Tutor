# C design 3: leak guard, failures and limits

[Milestone C design](README.md) · Previous: [help flow](02-help-flow.md) · Next: [own problems](04-own-problems.md)

## Leak guard (every response, every model, including fallbacks)

1. **Extract math:** every `$...$`, `$$...$$` and `\[...\]` span, plus a bare `=` expression on
   its own line. At most 20 candidate expressions per response; more counts as a block.
2. **Check equivalence** of each candidate with the answer using the existing parser and
   verifier in the sandboxed worker pool, with a per-check timeout. Also check the right-hand
   side of `y' = ...` forms.
3. **Choice problems:** also block a mention of the correct choice letter as an answer
   ("(a)", "option a") or its exact LaTeX.
4. **Block on a match, a timeout or a checker error.** The guard fails closed: an unchecked
   response is never shown as checked. On a block, log a leak event, retry once with a stricter
   instruction, and if that also blocks, show a fixed safe message with the citation:
   "Here's a nudge without the answer: re-read §X.Y."

Known limit: an answer written out in words ("two x cos x minus ...") is not caught. The
evaluation scores prose leakage by hand, and the write-up states this limit.

On hints-only own problems (C3) there is no answer, so the guard cannot run; those responses
are labeled accordingly (section 4).

## Failures

| Failure | Student sees |
|---|---|
| Claude timeout (15 s) or API error | "Hints are unavailable right now." Practice keeps working. |
| Model abstains | "I can't answer that from the textbook." plus the nearest section link |
| Invalid JSON or unknown citation IDs | One retry; then unknown IDs are dropped; none left counts as abstain |
| Rate limit or budget reached | "You've reached the help limit for now." |

No failure changes grading, tries or the practice state.

## Limits (settings, changeable without code edits)

| Limit | Initial value |
|---|---|
| Help requests per student | 30 per hour, 150 per day |
| Uploads per student (C3) | 10 per day |
| Site-wide spend | $15 per month, from logged token costs; above it help turns off |
| Per request | 1,000 output tokens, 6 passages, 15 s timeout, Haiku at low effort |

Also set a matching spend limit in the Anthropic console and keep auto-reload off.

## Help event log (`help_events`)

- Request: user, session item, problem and version, help type, hint level, confusion ID.
- Retrieval: retrieved chunk IDs and scores; cited IDs after validation.
- Generation: model, prompt version, tokens, cost, latency, retries, `use_case` label (C2).
- Outcome: shown, abstained, blocked (with leak reason), failed (with reason).
- Experiment: assigned A/B arm (`none` until the LoRA ships) and actual serving model.
- Follow-up: verdict of the next attempt on the same item, linked afterward.
- Free-text questions are stored for evaluation; "Clear history" deletes them with the rest.
