# Readiness, container and release debugging

[Debugging index](README.md) · [Runbook](../runbook.md) · [Host record](../host.md)

## Current release gap (2026-10-21)

Tasks 10–14 add a database and worker pool, but task 16 has not wired persistence/migrations
into Docker. `Dockerfile` does not copy Alembic files or create writable application storage;
`deploy/compose.yaml` has only Caddy volumes. `tests/container/smoke.sh` still assumes the
milestone A image. Its readiness check is expected to fail on the current branch.
This is a source-inspection finding, not a fresh Docker or remote CI run.

## Readiness decision path

Owner: `src/mathtutor/web/app.py`. `/healthz` alone does not establish readiness.

| `/readyz` reason | Inspect | Next check |
|---|---|---|
| `no_servable_problems` | Bundle, schema and review status | Offline `content_check`; six reviewed items currently exist |
| `database_unavailable` | Database URL, parent directory, permissions | Run migrations with the same URL as the app |
| `verifier_pool_down` | Lifespan startup and worker health | App logs and pool/process-boundary tests |

Database readiness currently performs `SELECT 1`; it does not prove migrations are current.
A missing schema may surface only when using accounts/practice. Do not bypass migrations.
For a source checkout use [development setup](../development.md). For Docker complete
[task 16](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/16-release.md).

## CI ownership

- `.github/workflows/ci.yml`: Python tests/checks plus generated and reviewed verifier gates;
  Node tests plus compiled-content consistency; e2e and container depend on both.
- Current `e2e` job migrates a temporary SQLite database and runs uvicorn directly.
  Task 16 moves it onto the image with a migrated volume.
- [Historical green runs](../../superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md)
  predate the app track. Do not cite them as current container or deployment evidence.
- For documentation-only failures: `uv run python tools/check_docs.py` checks Markdown
  line limits and relative file links. Split by responsibility and link each child.

## Release exit checks still required

1. Create writable `/data` owned by UID 10001, copy migrations and wire a migration service.
2. Pass container smoke with persistent storage and a real API submission.
3. Run browser smoke against the container; retain logs for any failure.
4. Complete/review task 15 content and rerun verifier gates after the content change.
5. Measure Linux memory with 16 simultaneous submissions; choose worker/cap settings from
   measurements. Windows tests cannot establish `RLIMIT_AS` containment.
6. Record deployed health, readiness and browser evidence in the host record; publish supported
   expressions and latency/accuracy evidence. Keep prior measurements dated.

[Task 16](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/16-release.md) owns the exact
implementation checklist. No host commands or deployments were performed in this docs pass.
