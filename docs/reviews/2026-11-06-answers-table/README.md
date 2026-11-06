# 2026-11-06 answers table review: Codex brief

[Reviews](../README.md) · [Plan](../../superpowers/plans/2026-11-05-answers-table/README.md) ·
[Design D1–D12](../../superpowers/plans/2026-11-05-answers-table/00-design.md) ·
[Handoff](../../../handoff.md)

Scope: branch `answers-table` from merge-base `3c3d939` to its release. Worktree:
`.claude/worktrees/answers-table`. Release state and remaining gates are in
`03-findings.md`; Thomas tests the live browser after deployment.

Built by Claude subagents, one task at a time; each task was reviewed for spec compliance and
quality, then a final whole-branch review. Controller rulings: [01-rulings.md](01-rulings.md).
Decisions still owed by Thomas: [02-open-decisions.md](02-open-decisions.md).
Codex review and release dispositions: [03-findings.md](03-findings.md).

## What changed

| Commit | Change | Check |
|---|---|---|
| `a613735`, `6caa33b` | Task 1: `answers` replaces `submissions` + `attempt_results` (migration 0006); `user_id`, `attempt_no`, `mistake_type`; Text-backed exact `mathjson`; verdict by conditional UPDATE; queries in `store/answers.py` | data copy and downgrade on a real DB shape; recovery/regrade races |
| `1230c51` | Task 2: attempts oldest → newest everywhere with `attempt_no`; golden prompt test | hint prompt text byte-identical to C1 |
| `b0ff055` | Task 3: ladder = mistakes made per type (cap 3); one hint per attempt, fixed `try_again` text; `help_requests.answer_id`; slimmer `item_help_state` (migration 0007); `MAX_TRIES` 5 | admission order, replay of fixed messages, clear-history interaction |
| `939f86d` | Task 4: background Haiku classifier for every applied wrong answer (one worker, bounded queue, ledger `kind="classify"`, write-once label); privacy copy | spend under the $10 month cap; logging; shutdown |
| `f0240c9`, `1e8fe7d` | Task 5: merge of local `main` (README); README, handoff, runbook deploy notes | README claims match code; deploy order |

Final-review fixes, if any, are listed at the end of [01-rulings.md](01-rulings.md).

## Evidence

Full pytest 1699 passed, 3 skipped, 1 known timing-flaky test that passes alone; ruff, format,
mypy clean; verifier gate B FA 0/50, FR 0/49; `check_docs` OK; `npm test` 50/50. Not run:
Docker image, container smoke and help e2e (no Docker on this PC); no paid calls; no host.

## Please check

1. Migrations 0006 → 0007 on a copy of the live database: row counts, attempt numbering, the
   one carried-over label per item, `PRAGMA foreign_key_check`, and downgrade.
2. Behavior change vs C1 evidence: the measured C1 results used 3 tries and a ladder per hint
   given. Is the README disclosure enough, and do the dev cases need new level labels?
3. Privacy: every wrong answer now goes to Anthropic even without a help click. Is the new
   notice accurate and sufficient (`practice.html`, `docs/ops/security.md`)?
4. Prompt identity: the classifier prompt is hashed into the hint `prompt_id` and its own
   prompt id is not recorded with labels (ledger item in 01).
5. Anything a deploy on the 1 GB host would trip over (worker thread, queue, `migrate`).

## Live deploy (2026-11-06)

Claude deployed `main` `05053b2` (image built at `e14485e`). App stopped; SQLite backup API
copy `/srv/backups/mathtutor-pre-answers-live-20261106T232913Z.db` (integrity ok, 0005,
26 submissions). `migrate` 0005→0007 exit 0; `audit_answers_migration.py` on backup vs live:
`PASS answers=26 graded=26 items=18 labels=2`; `foreign_key_check` empty; `/readyz` ready,
22 servable. Thomas's browser acceptance check: pending.
