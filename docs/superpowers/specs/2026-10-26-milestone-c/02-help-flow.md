# C design 2: help flow

[Milestone C design](README.md) · Previous: [components](01-components.md) · Next: [guard and limits](03-guard-and-limits.md)

## Request

`POST /api/help` (authenticated, CSRF-protected like the existing practice API):

```json
{ "session_item_id": "...", "item_revision": 7,
  "help_type": "hint | feedback | explain | question",
  "confusion": "explain only: an ID from the topic's confusion list",
  "question": "question only (C2): free text, at most 500 characters" }
```

The browser sends no problem text or answers. The server loads everything else itself, so a
client cannot supply fake context.

## Server-owned context

- Problem statement, topic and version; answer kind (expression or choice).
- The student's last 3 attempts on this item with their verdicts; tries used.
- Hint level for this item: 1 → 2 → 3, rising with each hint request, capped at 3.
- A recorded misconception matched by the latest wrong answer, checked through the existing
  bounded SymPy path (choice problems: the chosen distractor's note).

## Help types

| Type | Available | Behavior |
|---|---|---|
| Hint | any time | L1 concept reminder; L2 targeted next step; L3 fuller worked explanation that stops before the final expression |
| What did I do wrong? | after a wrong answer | Points at the specific error in the last attempt without correcting it outright |
| Explain this | any time | Student picks from a short per-topic confusion list; explains that idea |
| Ask a question (C2) | any time | Free text; the model also labels the use case (hint, feedback or explain), which is logged to measure routing |

Confusion lists live in versioned content files per topic, about 3–5 entries each.

## Retrieval

Query: problem statement + topic + help type + confusion or question text. BM25 top 6, with a
small score boost for chunks from the problem's own section. Retrieved IDs are logged.

## Generator output

JSON validated against a schema (structured outputs for Claude; the same schema for Qwen):

```json
{ "text": "markdown with LaTeX in $...$", "source_ids": ["c1-3.6-ex2"], "abstain": false,
  "use_case": "question type only: hint | feedback | explain" }
```

`abstain` is true when the question is out of scope or the passages do not support an answer.

## What the student sees

Hint text with rendered math, then a source line resolved from server metadata, for example:
"OpenStax Calculus Vol. 1, §3.6 The Chain Rule ↗ · CC BY-NC-SA 4.0". Links come only from the
corpus manifest, never from model text. Student-facing text uses US spelling.
