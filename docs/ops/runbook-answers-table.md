# Runbook: deploy the answers table (migrations 0006, 0007)

Part of the [C1 runbook](runbook-c1.md); same conventions as the [runbook](runbook.md): host
commands run from `/srv/mathtutor`, with `C="sudo docker compose -f deploy/compose.yaml"`.

Order matters; the migrations rewrite `submissions` and `attempt_results` into `answers`.

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
   sudo docker run --rm -e MATHTUTOR_SECRET_KEY=<any value> \
     -v <copy-dir>:/data mathtutor:local alembic upgrade head; echo $?
   ```
   Delete the copy afterward. If it does not print 0, stop: do not touch the live volume.

## Live deploy

1. Back up the DB to `/srv/backups/`; `git pull --ff-only`; build the image.
2. Run `migrate`; it must exit 0. Do not start `app` otherwise.
3. Start `app` and check `/readyz`.
4. Submit one wrong answer; its `answers` row has `attempt_no` 1 and, within a minute, a
   `mistake_type`.
