# C design 3: leak guard, failures and limits

[Milestone C design](README.md) · Previous: [help flow](02-help-flow.md) · Next: [own problems](04-own-problems.md)

## Leak guard (every response, every model, including fallbacks)

Review amendment: this is a supported-expression detector, not proof that text cannot reveal
an answer. [C-R1](../../../reviews/2026-10-26-milestone-c/01-guard.md) explains the distinction.

1. **Extract from final display text:** support `$...$`, `$$...$$`, `\(...\)` and `\[...\]`,
   standalone equations and RHS forms such as `y' = ...`. Recognized malformed math blocks;
   at most 20 candidates, with byte/node/depth caps and one total deadline, never 20 full waits.
2. **Parse in a bounded adapter:** existing Python verification accepts MathJSON, not arbitrary
   LaTeX. Add a pinned server-side parser producing raw trees for the allowlist translator.
   No unrestricted `eval`, `parse_expr` or `sympify`; no model AST trusted over displayed text.
3. **Classify `leak | no_match | unchecked`:** formula equality blocks before domain rejection.
   A grading `incorrect` verdict alone is not clearance. Supported certified inequality can
   clear a candidate; parse rejection, uncertain comparison, timeout, busy or worker error blocks.
4. **Answer kinds:** numeric answers need exact/rounding-aware leakage rules. Choices need
   correct-letter detection AND formula matching against the correct choice where parseable.
   Unsupported choice text/formulas are unchecked; elimination/paraphrase also needs human review.
5. **Fail closed on recognized candidates:** block if any candidate leaks/is unchecked. Empty
   extraction means `no_detected_math`, not "proved safe"; prose leakage remains possible.
6. **Deliver only after validation:** one shared repair retry at most, also fully guarded.
   If it fails, return a fixed section nudge using validated metadata, or "Hints unavailable"
   when no relevant section exists. Never echo rejected output or stream before guarding.

Unsupported general-rule notation may block useful hints; measure false blocks and coverage.
Prose, undetected notation, choice elimination and cumulative L1–L3 disclosure are evaluated
by hand. Do not advertise "never leaks". External textbook pages are outside this text guard.
Hints-only C3 has no reference answer: skip the guard, label/log it, and report separately.

## Failures

| Failure | Student sees |
|---|---|
| Total deadline or API error | "Hints are unavailable right now." Practice keeps working. |
| Model abstains | Fixed abstention text; a section link only if a relevant one is known |
| Invalid JSON, refusal/truncation or unknown citation IDs | Reject output; bounded repair if eligible, then fixed abstention |
| Rate limit or budget reached | "You've reached the help limit for now." |
| Stale item, deletion or conflicting request ID | No hint displayed; refresh/reconcile state |

No failure changes grading, tries or the practice state.

## Limits (settings, changeable without code edits)

| Limit | Initial value |
|---|---|
| Help requests per student | 30 per hour, 150 per day |
| Uploads per student (C3) | 10 per day |
| Site-wide spend | $15/month admission budget; durable worst-case reservations before calls |
| Per help request | 1,000 output tokens per call, 6 passages, 15 s total, Haiku at low effort |
| Provider calls | At most 2 total; SDK retries disabled; no retry of ambiguous billed timeout |

Input/context and global concurrency bounds are C-P1 prerequisites. Upload reading has its
own bounded workload (C-P3). [State/accounting](06-state-and-accounting.md) owns budget semantics,
retry ownership and restart behavior; verify provider console controls and keep auto-reload off.

## Help event log (`help_events`)

- Request: request ID, user, item/revision, problem/version, help type/level, confusion, context cutoff.
- Retrieval: corpus/index/config hashes, retrieved chunk IDs/scores and validated citations.
- Generation: requested/actual model, prompt/schema/parser/guard versions, tokens/cost/latency per call.
- Outcome: eligible delivery, abstained, blocked/unchecked, stale or failed with reasons; C2 label.
- Experiment: assigned A/B arm (`none` until the LoRA ships) and actual serving model.
- Follow-up: next eligible attempt ID/verdict and exposure timing, linked afterward.
- Private question/output records are deletable; usage is an independent content-free ledger.
  "Clear history" behavior is explicitly amended in [state/accounting](06-state-and-accounting.md).
