# Help evaluation (C1)

[Gates and case mix](../../docs/superpowers/plans/portfolio-mvp/milestone-c/c1/02-gates.md) ·
[Protocol](../../docs/superpowers/specs/2026-10-26-milestone-c/08-evaluation-protocol.md) ·
[Rubric v1](rubric/v1.md)

Offline evaluation of Claude-written help: a manual script that needs the real key, never CI.
Each case goes through the production path (`assemble_context` → `HelpPipeline.run`: BM25,
prompt, repair, leak guard in a real one-worker verifier pool). A blind judge scores every raw
output; `gates.py` applies 02-gates mechanically to the delivered results.

**Status 2026-10-27:** 60 help cases and 40 retrieval queries are drafts
(`reviewed_by: needs_review`). The runner refuses them until Thomas reviews them (step 6).

## Files

| Path | Content |
|---|---|
| `cases/dev.jsonl`, `cases/holdout.jsonl` | 36 / 24 help cases, grouped by problem (holdout: 7 problems, 3 topics) |
| `retrieval/dev.jsonl`, `retrieval/holdout.jsonl` | 28 / 12 book queries with relevant chunk ids, grouped by section |
| `rubric/v1.md` | the judge's instructions (also yours for the audit) |
| `results/<run_id>/` | `summary.md`, `run.json`, `audit.csv` (commit) and `results.jsonl` (git-ignored) |

A case has one category tag (02-gates mix), `known_error` when it counts toward the primary
measure, `attempts` (LaTeX, oldest first; option ids for choice problems) and a `note` for you
and the judge (never in the help prompt). Out-of-scope cases are no-evidence cases: they
withhold chapters 3–6 from retrieval, so only limits/functions passages remain and the right
answer is to abstain. Every drafted attempt was graded `incorrect` by the real checker.

## Step 6: review (Thomas)

1. For each case: is the attempt realistic and wrong, the note right, the category and help
   type sensible? Edit or drop, then set `"reviewed_by": "tg"`. Keep the mix: dropping a case
   needs a replacement in the same split and category, or `test_eval_drafted_sets.py` fails.
2. For each query, read the cited chunks and keep only ids that answer it; add any missing
   one. Show a chunk: `uv run python -c "import json; [print(r['text']) for r in map(json.loads, open('content/corpus/chunks.jsonl', encoding='utf-8')) if r['chunk_id']=='c1-3.6-rule1']"`.
3. Also approve or edit `rubric/v1.md` and the 12 confusion labels (`content/help/confusions.json`).
4. Free check on dev labels: `uv run python -m mathtutor.help.eval.run --split dev --retrieval-only`
   (`--draft` allows unreviewed rows). The holdout refuses any run without `--freeze`.
5. Run `uv run pytest -q tests/unit/help/test_eval_drafted_sets.py`, then commit the reviewed sets.

## Step 7: paid development runs ($5 credit: always `--max-usd 4`)

Set `MATHTUTOR_ANTHROPIC_API_KEY` in the shell (tests never read it), recheck list prices
against `tariffs` in `help_config.json` (C-O5), then:

```
uv run python -m mathtutor.help.eval.run --split dev --models claude-haiku-5-5,claude-sonnet-5-5 --max-usd 4
uv run python -m mathtutor.help.eval.run --split dev --models claude-haiku-5-5 --no-retrieval --no-judge --max-usd 4
```

The second is the retrieval baseline: with no passages every case abstains before any call
($0). The runner prints the spend after each case and stops before any call (help or judge)
whose worst case would pass the cap: Haiku 1,300 µ$, Sonnet 26,000 µ$ per help call, judge
64,000 µ$ (12k input / 4k output on Sonnet). Expect about $1.5–2.5 for the first command.
Iterate prompts on dev only; every run gets its own `results/<run_id>/`. The summary applies
the selection rule when both models ran; write the chosen model into `help_config.json`.

## Step 8: audit (Thomas)

Open `results/<run_id>/audit.csv`. Rows with a non-empty `audit` column are required: the
stratified random 20% (`random`, by help type and topic) and every `flagged:` row (leak,
endorsement, math error, guard miss, answer-substring heuristic, unjudged). Fill the
`human_*` columns (`none|expression|prose` for leak, `y|n` otherwise; blank keeps the
judge's label), then:

```
uv run python -m mathtutor.help.eval.run --recompute evals/help/results/<run_id>
```

Your labels win; `summary.md` reports random-sample agreement separately from targeted rows.

## Step 9: holdout, once

Commit everything, then run with the chosen model on a clean tree at that commit:

```
uv run python -m mathtutor.help.eval.run --split holdout --models claude-haiku-5-5 --freeze <commit> --max-usd 4
```

Audit as in step 8, recompute, and commit `summary.md`, `run.json` and `audit.csv`. Exit
code 1 means a gate failed: that blocks release (Task 15) and turns those cases into
regression evidence; a new claim then needs fresh holdout cases.

## Watch items

- `max_output_tokens` is 1,000 with adaptive thinking on: a reply can stop at `max_tokens`
  and count as invalid. The summary's operational table reports the `max_tokens` count per
  model; if it is not rare, raise the limit (it raises the worst case) before the holdout.
- The judge (`effort: medium`, 4,000 output tokens) can also stop early; such cases show as
  `unjudged`, fail the `all_delivered_judged` gate and are flagged for you in `audit.csv`.
- Draft retrieval labels give dev Recall@6 0.66 (Hit@6 0.86): several queries list 3–5
  relevant chunks, and LaTeX-only queries retrieve poorly. Recall@6 is gated on the holdout.
- BM25 tokenizes ASCII letters only: "L'Hôpital" in the book does not match "Lhopital".
- Selection rule as encoded: Sonnet needs +10 points and every gate; otherwise Haiku if it
  passes; if Haiku fails, nothing ships even when Sonnet passes (02-gates read literally).
- Set the Anthropic console spend limit with auto-reload off before the paid runs.
