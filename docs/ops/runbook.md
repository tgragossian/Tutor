# Runbook

[Operations](README.md) · [Host](host.md)

All commands run on the host, from `/srv/mathtutor`. `C` is shorthand used below:

```bash
C="sudo docker compose -f deploy/compose.yaml"
```

## Update to the latest `main`

```bash
git pull --ff-only
sudo docker build --build-arg GIT_SHA=$(git rev-parse --short HEAD) -t mathtutor:local .
$C up -d                                 # runs `migrate` (alembic upgrade head), then app
$C ps -a                                 # migrate: Exited (0); app and caddy: Up
sudo docker image prune -f
curl -fsS https://<domain>/readyz        # expect "status":"ready"
```

- The SQLite database lives in the `app_data` volume at `/data/mathtutor.db`. The one-shot
  `migrate` service must exit 0 before `app` starts; if it fails, `$C logs migrate`.
- `docker compose down` keeps volumes; never add `-v`, which deletes every account.
- Pool size and per-worker memory cap come from `MATHTUTOR_POOL_SIZE` / `MATHTUTOR_POOL_MEMORY_MB`
  in `deploy/.env` (defaults 1 and 384); size them from [host sizing](host-sizing.md).

## Measure memory (load burst)

```bash
bash tools/load/measure.sh https://tutor.thomasgragossian.dev
```

16 users submit the slowest live dev case at once while memory is sampled; it prints peak
container memory, peak RSS of the app and verifier worker, and the lowest available memory.
Some `503 verifier_busy` replies are expected (queue of 8). It leaves 16 `load_*` accounts.
Paste the output into [host sizing](host-sizing.md).

## Logs and status

```bash
$C ps
$C logs -f app          # or: caddy
```

## Restart

```bash
$C restart app
```

## Roll back

```bash
git log --oneline -5                     # pick the last good commit or tag
git checkout <commit>
sudo docker build -t mathtutor:local .
$C up -d
```

Return to `main` with `git checkout main` once the fix is merged.
Milestone D replaces this with rollback by image digest.

## Rotate the secret

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
nano deploy/.env                         # replace MATHTUTOR_SECRET_KEY
$C up -d app                             # recreates the container with the new value
```

In milestone A nothing uses the key yet; from milestone B, rotating it logs everyone out.

## Where `.env` lives

`deploy/.env` exists **only on the host** (mode 600). It is git-ignored and excluded from the
image by `.dockerignore`. If it is lost, recreate it from `deploy/.env.example` with a new key.

## Costs

The AWS Budget alert emails at $10/month; it is not a spending cap.
