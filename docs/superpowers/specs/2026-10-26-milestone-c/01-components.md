# C design 1: components

[Milestone C design](README.md) · Next: [help flow](02-help-flow.md)

## Offline corpus build

Planned `tools/build_corpus` acquires whole-book teaching pages from OpenStax *Calculus Volume 1*
and builds `content/corpus/chunks.jsonl` plus a provenance manifest from a frozen local snapshot.
The [corpus contract](07-corpus-contract.md) owns deterministic rebuilds and completeness checks.

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
| `help/leak_guard.py` | Extraction and leak-result policy; bounded parser/worker adapters (section 3) |
| `intake/` | C3: read typed or uploaded problems, confirm, solve (section 4) |
| `store/` | Help reservations/events, independent usage ledger and C3 problem versions via migrations |
| `web/` | `POST /api/help`, help panel on the practice page, C3 "My problems" page |

`HelpService` steps:

1. Validate/reserve request identity, state and spend; gather bounded server-owned context.
2. Retrieve the top passages.
3. Build the prompt for the help type (versioned prompt files).
4. Call the `Generator`.
5. Validate schema and every citation ID against this request's retrieved set; reject unknown IDs.
6. Run the leak guard.
7. Revalidate item/privacy state, settle usage and return validated text plus resolved citations.

## Key properties

- **One contract for every model.** Same prompt content, schema and application checks for
  Claude and Qwen; log provider decoding differences. Base/LoRA use identical serving code.
- **No intentional answer disclosure.** The existing deterministic **Reveal** action (after
  three wrong tries) stays the answer action. The guard applies at every level but cannot
  prove absence of prose or cumulative leaks; [section 3](03-guard-and-limits.md) owns this limit.
- **Help does not consume tries.** Every help event is logged so assisted and unassisted
  attempts stay distinguishable.
- **Untrusted inputs.** Student text and retrieved passages are data inside clearly delimited
  blocks, never instructions. An LLM response never changes a deterministic verdict.
- **Memory.** A whole-book BM25 index is expected to be tens of MB. Measure on the host in C1;
  move Lightsail to 2 GB if the measured headroom rule fails ([host sizing](../../../ops/host-sizing.md)).
- **Dependencies.** Add the `anthropic` SDK and a small BM25 implementation (library or local
  code, chosen in the plan). The API key comes from secrets configuration, never git.
- **Isolation.** Parser/solve/guard jobs need bounded worker interfaces; the current pool only
  grades `CheckRequest`. Keep SymPy out of the web process and preserve grading capacity.
- **Lifecycle.** [State/accounting](06-state-and-accounting.md) owns revisions, idempotency,
  deletion and usage. Missing provider/corpus disables help while core practice remains ready.
