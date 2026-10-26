# C design 1: components

[Milestone C design](README.md) · Next: [help flow](02-help-flow.md)

## Offline corpus build

`tools/build_corpus` fetches every page of OpenStax *Calculus Volume 1* and writes
`content/corpus/chunks.jsonl` plus a provenance manifest.

- Chunk at mathematical boundaries: definitions, theorems, rules, worked examples and
  explanatory subsections, about 300–500 tokens each. Math is kept as LaTeX.
- Each chunk carries a stable ID (for example `c1-3.6-ex2`), section number and title, page URL
  with anchor, and licence `CC BY-NC-SA 4.0`.
- The manifest records edition, base URL, retrieval date, per-page hashes and a corpus hash.
  The snapshot is a ShareAlike derivative and is distributed under the same licence (0004 §1).
- Re-running on the same snapshot gives the same IDs and hash. It is a script, not hand work.
- Exercises are not added to the graded bank here; that is the later bank project.

## Web application modules

New packages next to the existing `application/`, `verify/`, `store/` and `web/`:

| Module | Responsibility |
|---|---|
| `retrieval/` | Load `chunks.jsonl` at startup, build an in-memory BM25 index, return top-k with scores |
| `help/` | `HelpService`, the single entry point for all help (steps below) |
| `help/generator.py` | `Generator` protocol; `ClaudeGenerator` now, `QwenGenerator` after the LoRA |
| `help/leak_guard.py` | Expression extraction and SymPy equivalence checks (section 3) |
| `intake/` | C3: read typed or uploaded problems, confirm, solve (section 4) |
| `store/` | New tables `help_events` and (C3) `user_problems`, via Alembic migrations |
| `web/` | `POST /api/help`, help panel on the practice page, C3 "My problems" page |

`HelpService` steps:

1. Gather server-owned context (problem, attempts, tries, matched misconception).
2. Retrieve the top passages.
3. Build the prompt for the help type (versioned prompt files).
4. Call the `Generator`.
5. Validate citations: only IDs from this request's retrieved set are kept.
6. Run the leak guard.
7. Log a help event and return text plus resolved citations.

## Key properties

- **One contract for every model.** Same prompt, JSON output schema and checks for Claude and
  Qwen, so the LoRA A/B compares like with like.
- **The LLM never reveals the answer.** The existing deterministic **Reveal** action (after
  three wrong tries) stays the only way to see it, so the leak guard applies at every level.
- **Help does not consume tries.** Every help event is logged so assisted and unassisted
  attempts stay distinguishable.
- **Untrusted inputs.** Student text and retrieved passages are data inside clearly delimited
  blocks, never instructions. An LLM response never changes a deterministic verdict.
- **Memory.** A whole-book BM25 index is expected to be tens of MB. Measure on the host in C1;
  move Lightsail to 2 GB if the measured headroom rule fails ([host sizing](../../../ops/host-sizing.md)).
- **Dependencies.** Add the `anthropic` SDK and a small BM25 implementation (library or local
  code, chosen in the plan). The API key comes from secrets configuration, never git.
