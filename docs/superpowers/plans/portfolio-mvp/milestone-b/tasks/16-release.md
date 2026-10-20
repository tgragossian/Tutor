# Task 16: Release — volume, migrations, memory, deploy

[Milestone B plan](../README.md) · [Spec 09](../../../../specs/2026-10-13-portfolio-core/09-operations.md) · [Spec 08](../../../../specs/2026-10-13-portfolio-core/08-verifier-evaluation.md)

Release also needs resolved [evaluation follow-ups](../05-follow-ups.md), reviewed dev results,
and Linux pool/memory evidence; the Windows suite does not establish these.

**Status (2026-10-19):** not started; paths below are planned outputs.
Dependencies checked against the [file map](../01-file-map.md) and [rulings](../02-execution-rulings.md).

**Files:**
- Create: `tools/load/submit_burst.py`, `docs/verifier/README.md`, `docs/verifier/supported.md`, `evals/verifier/results/dev-b.md`
- Modify: `Dockerfile`, `deploy/compose.yaml`, `tests/container/smoke.sh`, `docs/ops/host.md`, `docs/ops/runbook.md`, `src/mathtutor/settings.py`, `README.md`, `docs/README.md`

**Interfaces:**
- Consumes: everything above. `Settings` gains `pool_size: int = 1` and `pool_memory_mb: int = 384` (env `MATHTUTOR_POOL_SIZE`, `MATHTUTOR_POOL_MEMORY_MB`), passed to `VerifierPool` in `create_app`.
- Produces: the deployed practice loop and its published measurements.

- [ ] **Step 1: Container changes, test first.** Extend `smoke.sh` (it fails first):
  - `/data` is a volume; inside the container `stat -c %u /data` is `10001` and `/data/mathtutor.db` is created by migrations.
  - A one-shot `docker run ... mathtutor:local alembic upgrade head` succeeds, then the app container reports `/readyz` 200.
  - One real submit through the API (register, start, submit the 221 answer) returns `"status":"correct"`.
- [ ] **Step 2: Implement.**
  - `Dockerfile`: copy `alembic.ini` and `migrations/`; `RUN mkdir /data && chown 10001:10001 /data`; `ENV MATHTUTOR_DATABASE_URL=sqlite:////data/mathtutor.db`; `ARG GIT_SHA` → `ENV MATHTUTOR_GIT_SHA`.
  - `compose.yaml`: named volume `app_data:/data`; a `migrate` service (same image, `command: alembic upgrade head`, `restart: "no"`); `app` has `depends_on: {migrate: {condition: service_completed_successfully}}`.
  - CI: move task 15's `e2e` job onto the container (start the image with a temp volume after the migrate run, then run the script against port 18000).
  - Run `bash tests/container/smoke.sh` (or push and watch CI). Expected: PASS.
- [ ] **Step 3: Measure memory (spec 09).** `tools/load/submit_burst.py --base-url URL --users 16` registers 16 users and fires 16 concurrent submits of the heaviest dev case. Thomas runs it against the server while running `free -m` and `sudo docker stats --no-stream` on the host. Record app, worker (peak RSS), Caddy and OS in `host.md`. Set `MATHTUTOR_POOL_SIZE` and `MATHTUTOR_POOL_MEMORY_MB` in `deploy/.env` from the numbers (rule: workers × memory cap + app + Caddy + OS ≤ 85% of RAM); if no setting fits, propose the 2 GB bundle to Thomas instead.
- [ ] **Step 4: Deploy (Thomas, on the host).** The runbook's update section gains the migrate step:
  ```bash
  cd /srv/mathtutor && git pull --ff-only
  sudo docker build --build-arg GIT_SHA=$(git rev-parse --short HEAD) -t mathtutor:local .
  sudo docker compose -f deploy/compose.yaml up -d && sudo docker image prune -f
  ```
  Then verify from outside: `/readyz` 200, and run `BASE_URL=https://tutor.thomasgragossian.dev npm run e2e --prefix tools`. Record outputs in `host.md`.
- [ ] **Step 5: Publish results.**
  - `evals/verifier/results/dev-b.md`: metrics with Wilson intervals and denominators, broken down by kind × reason × method; latency p50/p95 for worker and queue on the named host from step 3 (reported, not gated).
  - `docs/verifier/supported.md`: the allowlist in plain words, the domain policy, what abstains, known limitations (e.g. `\cos x\,(...)` parses as cos of a product; inverse trig not yet supported), and the "resource containment, not a sandbox" wording.
  - `README.md`: status "milestone B: practice loop live", links to the two documents above and `contracts/`.
- [ ] **Step 6:** Update `handoff.md` and `docs/ops/hours.md` (actual hours per task).
- [ ] **Step 7: Commit** `feat: persistent data volume, migrations on deploy; milestone B results`.
