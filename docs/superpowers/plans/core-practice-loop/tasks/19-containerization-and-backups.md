[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 879–895. Review findings remain unresolved.

### Task 19: Containerization and backups

**Files:**
- Create: `deploy/Dockerfile`, `deploy/docker-compose.yml`, `deploy/Caddyfile`, `deploy/backup.sh`, `deploy/entrypoint.sh`, `.dockerignore`, `tests/test_deploy_files.py`

**Interfaces:**
- **Image:** `python:3.12-slim`, a non-root user, `uv sync --frozen --no-dev`. `entrypoint.sh` runs `alembic upgrade head` and then `uvicorn mathtutor.web.app:app --host 0.0.0.0 --port 8000`. A `HEALTHCHECK` hits `/healthz`.
- **Compose:** services `app` (volume `./data:/app/data`, `env_file: .env`) and `caddy` (ports 80/443, `Caddyfile` with `{$DOMAIN} { reverse_proxy app:8000 }`).
- **`backup.sh`:** `sqlite3 data/mathtutor.db ".backup /tmp/…"` → `aws s3 cp` to `s3://$BACKUP_BUCKET/mathtutor-<UTC date>.db`, then deletes all but the newest 14. It is run nightly by host cron (documented in the README).

- [ ] **Step 1: Write the failing test** (static checks): the Dockerfile has a non-root `USER` and a `HEALTHCHECK`; the compose file defines no secrets inline; `backup.sh` keeps exactly 14.
- [ ] **Step 2:** Run `uv run pytest tests/test_deploy_files.py -v`. Expected: FAIL, then implement.
- [ ] **Step 3:** Run `docker build -f deploy/Dockerfile -t mathtutor .`, then `docker run` with a temp `.env`, then `curl localhost:8000/healthz`. Expected: `{"status":"ok"}`.
- [ ] **Step 4: Commit** `build: Docker image, compose with Caddy, S3 backup script`.

---

<!-- End preserved source. -->
