# Runbook: deploy the answers table (migrations 0006, 0007)

Part of the [C1 runbook](runbook-c1.md); same conventions as the [runbook](runbook.md): host
commands run from `/srv/mathtutor`, with `C="sudo docker compose -f deploy/compose.yaml"`.

Order matters; the migrations rewrite `submissions` and `attempt_results` into `answers`.
Resolve the [Codex findings](../reviews/2026-11-06-answers-table/03-findings.md) and
[owner decisions](../reviews/2026-11-06-answers-table/02-open-decisions.md) before deploying.

## Before the live deploy

1. Container smoke with the help browser e2e, on a machine with Docker and a clean tree. It
   builds `mathtutor:local` and, with `E2E=1`, also runs the browser tests (the help e2e uses
   the scripted generator on its own volume), as `.github/workflows/ci.yml` does:
   ```bash
   E2E=1 bash tests/container/smoke.sh
   ```
2. Rehearse the migration on a copy of the latest live backup, never the live volume. The
   repo has no backup or restore command, so in words: copy the newest file in
   `/srv/backups/` to `mathtutor.db` in an empty directory and make that directory owned by
   uid 10001 (the image's user, see `smoke.sh`). Then run the image's own migrate command,
   as `smoke.sh` and the `migrate` service in `deploy/compose.yaml` do, against that
   directory, and check it exits 0:
   ```bash
   COPY_DIR=/absolute/path/to/backup-copy
   sudo docker run --rm -e MATHTUTOR_SECRET_KEY=temporary-rehearsal-key \
     -v "$COPY_DIR:/data" mathtutor:local alembic upgrade head; echo $?
   ```
   Before and after, record row counts: `answers` must match old `submissions`, and graded
   answers must match old `attempt_results`. Check consecutive applied `attempt_no` values
   per item, the carried mistake labels, and empty `PRAGMA foreign_key_check` output.
   Test downgrade on a second copy, retaining the first as migration evidence. If any check
   fails, stop: do not touch the live volume.

## Live deploy

1. Back up the DB to `/srv/backups/`; `git pull --ff-only`; build the image.
2. Run `migrate`; it must exit 0. Do not start `app` otherwise.
3. Start `app` and check `/readyz`.
4. Submit one wrong answer; its `answers` row has `attempt_no` 1 and, within a minute, a
   `mistake_type`.

## Thomas's live acceptance check

Before sharing the updated demo, Thomas tests it in the browser after deployment:

1. Sign in with an existing account and inspect pre-migration session history; old answers
   and verdicts must still appear in order.
2. Use MathLive to submit wrong and correct answers; verify verdicts, attempt order, and
   five-try exhaustion. Check a choice problem and an `unable_to_verify` result too.
3. Ask for a hint after a wrong answer, then click Hint again. The repeat must use no
   model call; the next wrong attempt should unlock the next hint at the expected level.
4. Check *What did I do wrong?*, *Explain this*, *Show answer*, and the provider disclosure.
5. Clear history on an open item and check the hint behavior agreed in the owner decisions.

Record the date, deployed commit, migration result, and any failure in the
[answers-table review](../reviews/2026-11-06-answers-table/README.md). Do not call the
refactor live-tested or send the updated demo until this check passes.
