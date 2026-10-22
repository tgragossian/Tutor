# Readiness, container and release debugging

[Debugging index](README.md) · [Runbook](../runbook.md) · [Host record](../host.md)

## Storage and migrations in the container (2026-10-22)

The image copies `alembic.ini` and `migrations/`, sets `MATHTUTOR_DATABASE_URL` to
`/data/mathtutor.db` and owns `/data` as uid 10001. Compose mounts the `app_data` volume and
runs a one-shot `migrate` service (`alembic upgrade head`) before `app`.
`tests/container/smoke.sh` migrates a fresh volume, checks ownership, waits for `/readyz`
and grades one real answer (exercise 221) through the API. With `E2E=1` it runs browser smoke
against that image; CI supplies this flag. Host measurements and the sizing exception are
recorded in [host sizing](../host-sizing.md).

## Readiness decision path

Owner: `src/mathtutor/web/app.py`. `/healthz` alone does not establish readiness.

| `/readyz` reason | Inspect | Next check |
|---|---|---|
| `no_servable_problems` | Bundle, schema and review status | Offline `content_check`; 22 reviewed items currently exist |
| `database_unavailable` | Database URL, parent directory, permissions | Run migrations with the same URL as the app |
| `verifier_pool_down` | Lifespan startup and worker health | App logs and pool/process-boundary tests |

Database readiness currently performs `SELECT 1`; it does not prove migrations are current.
A missing schema may surface only when using accounts/practice. Do not bypass migrations.
For a source checkout use [development setup](../development.md). For Docker complete
[task 16](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/16-release.md).

## CI ownership

- `.github/workflows/ci.yml`: Python tests/checks plus generated and reviewed verifier gates;
  Node tests plus compiled-content consistency; the container job depends on both.
- The container job runs `E2E=1 bash tests/container/smoke.sh` against a migrated volume.
- [Evidence](../../superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md)
  separates fresh local tests from recorded image/host results and earlier milestone A runs.
- For documentation-only failures: `uv run python tools/check_docs.py` checks Markdown
  line limits and relative file links. Split by responsibility and link each child.

## Current review and remaining gates

1. [Whole-branch review findings](../../reviews/2026-10-22-milestone-b/README.md) are fixed
   ([dispositions](../../reviews/2026-10-22-milestone-b/06-dispositions.md)). Deploying ca54407+ runs migration 0003: `migrate` must exit 0.
2. Load diagnostics: `submit_burst.py` fails on anything but graded answers and
   `verifier_busy`, and on zero grades; `measure.sh` returns that status (B-R4 fix).
3. Retain Thomas's 1 GB / one worker / 384 MB exception; revisit sizing in milestone C.
   Windows tests cannot establish Linux `RLIMIT_AS` containment.
4. Record actual hours, rerun affected checks after fixes, and retain dated deployment evidence.

[Task 16](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/16-release.md) owns the exact
implementation checklist. No host commands or deployments were performed in this review.
