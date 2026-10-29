# Help evaluation (C1)

[Gates and case mix](../../docs/superpowers/plans/portfolio-mvp/milestone-c/c1/02-gates.md) ·
[Protocol](../../docs/superpowers/specs/2026-10-26-milestone-c/08-evaluation-protocol.md) ·
[Rubric v1](rubric/v1.md)

Offline evaluation of Claude-written help: a manual script that needs the real key, never CI.
Each case goes through the production path (`assemble_context` → `HelpPipeline.run`: BM25,
prompt, repair, leak guard in a real one-worker verifier pool). A blind judge scores parsed
non-abstaining outputs (including uncited baseline: R7); `gates.py` checks delivered results.

**Status 2026-10-28:** [C1-R4/R7 fixed locally](../../docs/reviews/2026-10-27-milestone-c1/11-debugging-fixes.md); owner release gates remain.
Reviewed 2026-10-29: cases 42/42 dev, 23/24 holdout; queries 12/12 holdout, 0/28 dev (run refuses).

## Files

| Path | Content |
|---|---|
| `cases/{dev,holdout}.jsonl` | 42 / 24 help cases, grouped by problem (holdout: 7 problems, 3 topics) |
| `retrieval/{dev,holdout}.jsonl` | 28 / 12 book queries with relevant chunk ids, grouped by home section |
| `rubric/v1.md` | the judge's instructions (also yours for the audit) |
| `results/<run_id>/` | `summary.md`, `run.json`, `audit.csv`, `audit_key.csv`, `spend.jsonl` (commit); `results.jsonl` (ignored) |
| `holdout-claims/<run_id>.json` | ids a holdout run used (cases, problems, queries, chunks); commit it |

A case has one category tag (02-gates mix), `known_error` when it counts toward the primary
measure, `attempts` (LaTeX, oldest first; option ids for choice problems) and a `note` for you
and the judge (never in the help prompt). Every drafted attempt grades `incorrect`.
- Out-of-scope cases withhold chapters 3–6 (2–6 for two tangent cases): the answer is abstain.
- `tell_me_answer`: repeated wrong attempts with a level-3 hint (or explain); no free text in C1.
- Hint levels (R35): 0 with no attempt (`start_step` 2: a second, concrete start). With attempts, the model labels the latest one's
  type: `expect_mistake_type`; `prior_hints` are each type's earlier hints (level = +1).

**Retrieval labeling policy:** label the 1–3 chunks that directly answer the query, most
direct first. Chapter summaries (`N.0` key terms/equations) and per-section "Key Concepts"
chunks are excluded unless the query asks for a summary. Applied identically to both splits;
the holdout was relabeled by this rule alone, without running retrieval on it. Evaluation
searches like production: configured roles plus the home-section boost (`section`).

## Step 6: review (Thomas)

1. Cases: is the attempt realistic and wrong, the note right, category, help type and (choice
   cases) `expect_mistake_type` and `prior_hints` sensible? Edit, then set `"reviewed_by": "tg"`. Dropping a case needs
   a replacement in the same split and category, or `test_eval_drafted_sets.py` fails.
2. Queries: read the cited chunks and apply the policy above. Show a chunk:
   `uv run python -c "import json; [print(r['text']) for r in map(json.loads, open('content/corpus/chunks.jsonl', encoding='utf-8')) if r['chunk_id']=='c1-3.6-rule1']"`.
3. Approve or edit `rubric/v1.md` and the 18 confusion labels (`content/help/confusions.json`).
4. Free dev check: `uv run python -m mathtutor.help.eval.run --split dev --retrieval-only`
   (`--draft` allows unreviewed rows). Retrieval-only holdout runs are refused; scoring belongs to its locked campaign.
5. Run `uv run pytest -q tests/unit/help/test_eval_drafted_sets.py`; commit the reviewed sets.

## Step 7: paid development runs ($5 credit)

After owner review, set `MATHTUTOR_ANTHROPIC_API_KEY`, recheck list prices against
`tariffs` in `help_config.json` (C-O5), set the console spend limit with auto-reload off, then:

```
uv run python -m mathtutor.help.eval.run --split dev --models claude-haiku-5-5,claude-sonnet-5-5 --max-usd 4
```

Worst case per call: Haiku 1,300 µ$, Sonnet 26,000 µ$, judge 64,000 µ$; spend prints per case.
Recorded estimate: $1.5–2.5 for that command; confirm tariffs before execution. The no-passage
baseline now reaches judge/audit/recompute with citation support N/A. Use `--no-retrieval`
with judging enabled; `--no-judge` is generation/cost diagnosis only. Iterate on dev only.
The summary applies the selection rule; write the chosen model into `help_config.json`.

## Step 8: audit (Thomas)

`results/<run_id>/audit.csv` is blind: items are `<case>-r<n>` with no model column; the
model mapping is in `audit_key.csv` (don't open it while labeling). Rows with a non-empty
`audit` column are required: the stratified random 20% (`random`, by help type and topic)
and every `flagged:` row. Fill `human_*` (`none|expression|prose` for leak, `y|n` otherwise;
blank keeps the judge's label), then
`uv run python -m mathtutor.help.eval.run --recompute evals/help/results/<run_id>`.
Your labels win everywhere, including the paired table.

## Step 9: holdout, once

Credit first: `uv run python -m mathtutor.help.eval.run --spent` totals every run's
`spend.jsonl`, interrupted runs included (an unsettled call counts at its worst case). Pass
the credit minus that total minus a margin (≥ $0.30) as `--max-usd`. A holdout claims its
cases, problems, queries and relevant chunks before retrieval scoring or provider calls.
Retrieval-only is dev-only; overlapping holdouts are refused before scores. A stopped run
needs fresh problems and queries, not reworded cases. Run ids are never reused.
Commit everything, then on a clean tree at that commit:

```
uv run python -m mathtutor.help.eval.run --split holdout --models <chosen> --freeze <commit> --max-usd <remaining>
```

Audit and recompute as in step 8; commit the results files. Exit code 1 means a gate failed:
release is blocked (Task 15) and those cases become regression evidence.

## Watch items

- `max_output_tokens` 1,000 can stop at `max_tokens` (counted per model); if not rare, raise it.
- The judge (`effort: medium`, 4,000 output tokens) can stop early: such cases are `unjudged`,
  fail `all_delivered_judged` and are flagged in `audit.csv`.
- Dev Recall@6 with the policy, tok-2 and the boost: 0.79 (MRR@6 0.66).
- Selection (R28): Sonnet if +10 points on the primary and every gate with nothing > 5
  points worse; otherwise Haiku if it passes; otherwise Sonnet if it passes; otherwise none.
