# Runbook

[Operations](README.md) · [Host](host.md)

All commands run on the host, from `/srv/mathtutor`. `C` is shorthand used below:

```bash
C="sudo docker compose -f deploy/compose.yaml"
```

## Update to the latest `main`

```bash
git pull --ff-only
sudo docker build -t mathtutor:local .
$C up -d
sudo docker image prune -f
curl -fsS https://<domain>/readyz        # expect "status":"ready"
```

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
