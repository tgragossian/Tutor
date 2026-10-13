# Task 7: Container, Caddy, CI smoke test

[Milestone A plan](../README.md) · [Spec 09](../../../../specs/2026-10-13-portfolio-core/09-operations.md)

**Files:**
- Create:
  - `Dockerfile`, `.dockerignore`
  - `deploy/compose.yaml`, `deploy/Caddyfile`, `deploy/.env.example`
  - `tests/container/smoke.sh`
  - `docs/ops/local.md`
- Modify:
  - `.github/workflows/ci.yml`: add the job `container`
  - `docs/ops/README.md`: link `local.md`

**Interfaces:**
- Consumes: `mathtutor.web.app:app_factory` and the environment variables from task 6.
- Produces:
  - the image `mathtutor:local`, which listens on 8000 and runs as uid 10001
  - `deploy/compose.yaml`, which task 8 uses unchanged on the host

**Human prerequisite (optional):** install Docker Desktop to run this locally. Otherwise CI runs the smoke test.

**Image:**
- Multi-stage build. The build stage uses a pinned `ghcr.io/astral-sh/uv` tag and runs `uv sync --locked --no-dev --no-editable` into `/app/.venv`.
- Runtime: a pinned `python:3.12-slim` tag. It copies the venv and `content/compiled/`, then creates a user `app` with uid and gid 10001.
- Settings: `ENV MATHTUTOR_ENV=production MATHTUTOR_CONTENT_PATH=/app/content/compiled/problems.json`, then `USER 10001`.
- `HEALTHCHECK`: Python `urllib` fetches `http://127.0.0.1:8000/healthz`.
- `CMD`: `uvicorn mathtutor.web.app:app_factory --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'`
  - This is safe only because port 8000 is never published. Only Caddy reaches it, over the compose network.
- `.dockerignore` excludes `.git`, `.venv`, `tools/node_modules`, `tests`, `docs`, `evals`, `.superpowers`, `*.db` and `.env*`.
- **No Node in the image** (constraint).

**Compose and Caddy:**
- **`app`:**
  - `image: ${MATHTUTOR_IMAGE:-mathtutor:local}`
  - `env_file: .env`
  - `restart: unless-stopped`
  - **no `ports:`**
- **`caddy`:**
  - a pinned `caddy:2.x` tag
  - ports `80:80` and `443:443`
  - mounts `./Caddyfile`, plus volumes for `caddy_data` and `caddy_config`
  - `depends_on: app`
- **`Caddyfile`:** `{$SITE_ADDRESS} { encode zstd gzip  reverse_proxy app:8000 }`
  - Locally, `SITE_ADDRESS=localhost` uses Caddy's internal CA. On the server it's the domain, which gets a Let's Encrypt certificate.
- **`deploy/.env.example`:** `MATHTUTOR_SECRET_KEY=` and `SITE_ADDRESS=localhost`, with a comment showing the command that generates a key.

- [ ] **Step 1: Write the failing smoke test** in `tests/container/smoke.sh` (bash, `set -euo pipefail`).
  - `docker build -t mathtutor:local .`
  - Assert `docker run --rm mathtutor:local id -u` prints `10001`.
  - Assert `docker run --rm mathtutor:local sh -c 'command -v node || echo none'` prints `none`.
  - Start the container with `-e MATHTUTOR_SECRET_KEY=$(head -c 48 /dev/urandom | base64) -p 127.0.0.1:18000:8000`, which publishes the port **for the test only**.
  - Poll `/readyz` for up to 30 s. Assert HTTP 200 and that `"servable":6` appears in the body.
  - Assert that the same container without a secret exits non-zero within 10 s.
  - Validate the compose file: `docker compose -f deploy/compose.yaml --env-file deploy/.env.example config -q`.
  - Clean up with a `trap`.
- [ ] **Step 2:** Run `bash tests/container/smoke.sh`. Expected: FAIL (there's no Dockerfile).
  - Without Docker locally, write the CI job first and observe the failure there.
- [ ] **Step 3: Implement** the Dockerfile, `.dockerignore`, compose file, Caddyfile and `.env.example` as specified above.
- [ ] **Step 4:** Run `bash tests/container/smoke.sh`. Expected: PASS.
  - Locally, also run `cp deploy/.env.example deploy/.env` (setting a real key), then `docker compose -f deploy/compose.yaml up`.
  - <https://localhost/readyz> should answer, after you accept Caddy's local certificate.
- [ ] **Step 5: CI job `container`.** It runs after `python` and `node` pass, on ubuntu-latest, with `bash tests/container/smoke.sh`.
- [ ] **Step 6: Write `docs/ops/local.md`** (≤ 40 lines). It covers:
  - building and running locally
  - creating `.env` and generating a secret
  - trusting Caddy's local CA, or using `curl -k`
  - stopping and cleaning up
- [ ] **Step 7: Commit** with the message `feat: container image, Caddy HTTPS proxy, CI smoke test`.
