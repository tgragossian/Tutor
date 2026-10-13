[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 400–411. Review findings remain unresolved.

## 10. Deployment

- **Image:** Dockerfile (python:3.12-slim) running uvicorn. Alembic `upgrade head` runs at container start.
- **Host:** an AWS Lightsail instance (~$5/mo) running `docker compose` with the app and **Caddy** (automatic HTTPS). This needs a domain (~$12/yr).
- **Data:** SQLite on a host volume. A nightly `sqlite3 .backup` is uploaded to S3, keeping the last 14 backups.
- **CI (GitHub Actions):**
  - ruff, mypy, pytest, verifier evaluation and image build on every push
  - on `main`: push the image to GHCR and deploy over SSH (`docker compose pull && up -d`)
- **Cost guard:** AWS Budget alert at $10/month.

---

<!-- End preserved source. -->
