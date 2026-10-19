# Running the container locally

[Operations](README.md)

Needs Docker Desktop. Commands run from the repository root.

## Build and smoke-test

```bash
bash tests/container/smoke.sh      # builds mathtutor:local and runs every check
```

## Configure

```bash
cp deploy/.env.example deploy/.env   # deploy/.env is git-ignored; never commit it
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the output after `MATHTUTOR_SECRET_KEY=` in `deploy/.env`. Set `SITE_ADDRESS=localhost` explicitly; the example leaves it empty.

## Run behind Caddy

```bash
docker build -t mathtutor:local .
docker compose -f deploy/compose.yaml up -d
curl -k https://localhost/readyz     # -k: Caddy's local CA is not trusted yet
```

To trust Caddy's local CA, copy out its root certificate and import it into your OS/browser:
`docker compose -f deploy/compose.yaml cp caddy:/data/caddy/pki/authorities/local/root.crt .` (or accept the browser warning).
Port 8000 is never published; only Caddy (80/443) is reachable.

## Stop and clean up

```bash
docker compose -f deploy/compose.yaml down        # keeps Caddy's certificates
docker compose -f deploy/compose.yaml down -v     # also deletes the caddy_data/config volumes
docker image rm mathtutor:local
```
