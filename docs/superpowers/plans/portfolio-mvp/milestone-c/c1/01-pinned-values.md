# C1 pinned values (resolves C-P1)

[C1 plan](README.md) · [Gates](02-gates.md)

Proposed by Claude on 2026-10-26 for Thomas's review. All values live in the versioned
`src/mathtutor/help/help_config.json` (Task 1); this table is its documentation.

## Provider and tariff

| Key | Value |
|---|---|
| `model` | `claude-haiku-5-5` (eval may set `claude-sonnet-5-5`) |
| `effort` | `low`; adaptive thinking left on (Haiku 5.5 default) |
| tariff `claude-haiku-5-5` | 100,000 / 500,000 micro-USD per 1M input / output tokens (prompts ≤100K) |
| tariff `claude-sonnet-5-5` | 2,000,000 / 10,000,000 micro-USD per 1M input / output tokens |
| `tariff_version` | `2026-10-26`; recheck list prices before the paid run (C-O5) |
| SDK | `max_retries=0`; per-call `timeout` = remaining request deadline |

Thinking tokens bill as output and count inside `max_tokens`, so the worst case per call is
`max_input_tokens × in + max_output_tokens × out` (Haiku: 8,000 × 0.1 + 1,000 × 0.5 = 1,300 µ$).

## Per-request bounds

| Key | Value |
|---|---|
| `deadline_s` | 15.0 for the whole request (queue, retrieval, calls, parse, guard) |
| `max_calls` | 2 generator calls per logical request, all repair reasons combined |
| `max_output_tokens` | 1,000 per call |
| `max_input_tokens` | 8,000 estimated as `ceil(utf8_bytes / 3)`; prompt builder trims to fit |
| field caps (bytes) | statement 1,500; each attempt LaTeX 400; misconception note 300; confusion text 300 |
| `passages` | 6 retrieved; each chunk ≤ 700 estimated tokens (hard ceiling from Task 5) |
| output text | ≤ 2,000 characters; `source_ids` 1–6 unique, or 0 when `abstain` |
| guard | ≤ 20 candidates, each ≤ 400 bytes, ≤ 200 parse nodes, depth ≤ 24; guard budget = min(5 s, remaining) |
| guard pool | separate `VerifierPool(size=1, deadline_s=2.0, queue_max=4, queue_wait_s=1.0, memory_mb=384)` |

## Admission

| Key | Value |
|---|---|
| per student | 30 admitted requests / rolling hour; 150 / rolling day (counted from the ledger) |
| global concurrency | 4 help requests in flight per process (semaphore); excess → `unavailable` |
| month budget | 15,000,000 µ$ (`$15`), UTC month; settled + reserved + uncertain + new worst case ≤ budget |
| uncertain | a reservation not settled within 120 s is `uncertain`; it counts at worst case until settled by hand |
| per item | one in-flight help request per `session_item_id` (help-state row lock) |

## Context and misconceptions

- Last 3 consumed attempts on the item (newest first): LaTeX + verdict status only.
- Misconception match: latest attempt is `incorrect`; expression/numeric match = existing checker
  returns `correct` against the misconception's compiled MathJSON with the answer's variable and
  domain; choice match = chosen id equals the entry's id. Note = text after `  # ` in the entry.
- `content_check` gains a rule: every misconception on a `human_verified` problem has a note.
- Excluded from prompts: reference answer, choice correctness, review notes, the user's name.

## Retrieval

BM25 `k1=1.2`, `b=0.75`; own-section boost ×1.3 (dev-tuned only, Task 6); roles allowed in C1:
definition, theorem, rule, example, explanation. Query cap 1,200 bytes; question text ≤ 500.
