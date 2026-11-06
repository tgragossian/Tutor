# C1 recheck: hint state and prompt provenance

[Recheck](07-recheck.md) · [Rulings](../../superpowers/plans/portfolio-mvp/milestone-c/c1/21-rulings.md)

Reviewed at `b16a206` on 2026-10-28. R35/R36 are accepted for the implemented scope below;
this is source/regression evidence, not a judgment of real model tutoring quality.

## R35: two-step level zero and per-mistake ladders

- [service.py](../../../src/mathtutor/help/service.py): `_hint_plan` offers level 0 before
  any wrong answer; `start_step` advances from 1 to 2 and then repeats. Each mistake type
  has its own delivered-hint count, capped at level 3.
- A new wrong attempt asks the model to choose a supported mistake type at a server-offered
  level. Further hints for that attempt reuse its recorded type. Finalization owns updates,
  so stale responses and replay cannot independently advance the ladder.
- [Hint tests](../../../tests/unit/help/test_hint_ladder.py) cover prompt levels, schemas,
  offered types and evaluation fields; [service tests](../../../tests/unit/help/test_service.py)
  cover persisted progression. Migration 0005 stores the new state.
- Labels are model judgments, not deterministic diagnoses. Owner review of the wording and
  evaluation labels remains necessary; the guard still cannot prove absence of prose leaks.

## R36: reproducible prompt-set identity

- [prompts.py](../../../src/mathtutor/help/prompts.py): `prompt_fingerprint` hashes all
  versioned Markdown prompt files, normalized source bytes of `prompts.py`, output schemas
  and mistake descriptions. Help records store `v1+<12 hex>`; run metadata records the hash.
- [Fingerprint tests](../../../tests/unit/help/test_prompt_fingerprint.py) check stability,
  wording/new-file changes, line-ending normalization and persistence on help rows.
- This identifies the instruction set, not the complete rendered request: dynamic context,
  retrieval contents, model/config, schema and corpus versions still matter for reproduction.
  The process caches templates and fingerprints; restart after editing deployed prompt files.

## Follow-through

Keep C2's additive prompt files versioned and fingerprinted. Rebase its plan onto the final
C1 fixes before implementing. C2 Q1–Q9 are recorded as decided in its worktree; the old
close-out text asking Thomas to answer Q1–Q8 is stale. A C2 plan review is still separate
work and is not claimed by this C1 recheck.
