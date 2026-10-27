# C design 2: help flow

[Milestone C design](README.md) · Previous: [components](01-components.md) · Next: [guard and limits](03-guard-and-limits.md)

## Request

`POST /api/help` (authenticated, CSRF-protected like the existing practice API):

```json
{ "help_request_id": "client-generated UUID", "session_item_id": 123, "item_revision": 7,
  "help_type": "hint | feedback | explain | question",
  "confusion": "explain only: an ID from the topic's confusion list",
  "question": "question only (C2): free text, at most 500 characters" }
```

The browser sends no problem text or answers. The server loads everything else itself, so a
client cannot supply fake context.
The example documents alternatives; the implementation schema uses enums and rejects fields
that do not apply to the selected type. C1 rejects `question`; C2 remains item-scoped.
Admission, replay and stale completion follow [state/accounting](06-state-and-accounting.md).

## Server-owned context

- Problem statement, topic and version; answer kind (expression, numeric or choice).
- The student's last 3 attempts on this item with their verdicts; tries used.
- Hint level (amended 2026-10-27, Thomas, ruling R35): 0 "how to start" before any wrong
  answer; then 1 → 2 → 3 while the student repeats the same mistake, capped at 3; a new
  mistake restarts at 1. The model only judges same or new; the server sets the level.
- A recorded misconception matched by the latest wrong answer, checked through the existing
  bounded SymPy path (choice problems: the chosen distractor's note).
- Match only reviewed misconception entries. Existing content has expression strings/compiled
  trees, not a typed explanatory-note contract; add reviewed labels and deterministic mapping.
  Unmatched work gets tentative feedback, not an invented verified diagnosis.
- Exclude reference answers, review notes and solution text from the generator prompt. The
  guard keeps the reference privately. Bound attempt/context fields and version the policy.

## Help types

| Type | Available | Behavior |
|---|---|---|
| Hint | active/exhausted item | L1 concept reminder; L2 targeted next step; L3 fuller explanation, still withholding the final answer |
| What did I do wrong? | after a wrong answer | Points at the specific error in the last attempt without correcting it outright |
| Explain this | active/exhausted item | Student picks from a short per-topic confusion list; explains that idea |
| Ask a question (C2) | active/exhausted item | Free text; model labels hint/feedback/explain for measurement, never to bypass checks |

Confusion lists live in versioned content files per topic, about 3–5 entries each.

## Retrieval

Query: problem statement + topic + help type + confusion or question text. BM25 top 6, with a
small score boost for chunks from the problem's own section. Retrieved IDs are logged.
Feedback also includes bounded wrong-attempt/misconception context. The
[corpus contract](07-corpus-contract.md) owns tokenization, bounds and no-context behavior.

## Generator output

JSON validated against a schema (structured outputs for Claude; the same schema for Qwen):

```json
{ "text": "markdown with LaTeX in $...$", "source_ids": ["c1-3.6-ex2"], "abstain": false,
  "use_case": "question type only: hint | feedback | explain" }
```

`abstain` is true when the question is out of scope or the passages do not support an answer.
Bound text and unique source IDs (at most 6); non-abstaining text needs a valid citation.
Refusal/truncation and malformed schema never become displayable text. C2 routing is descriptive;
all labels use the same guard. Review raw and delivered outcomes separately.

## What the student sees

Hint text with rendered math, then a source line resolved from server metadata, for example:
"OpenStax Calculus Vol. 1, §3.6 The Chain Rule ↗ · CC BY-NC-SA 4.0". Links come only from the
corpus manifest, never from model text. Student-facing text uses US spelling.
Validate before any display/streaming. Render only safe Markdown/math: no model HTML, links
or images. Response metadata binds request ID, item/revision, help sequence and terminal status.
