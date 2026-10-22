# Local development: milestone B

[Operations](README.md) · [Debugging](debugging/README.md)

Run from the main checkout or `milestone-b` worktree root. Both contain the practice loop
and migration 0003; container storage/migration wiring is implemented.

## Install and migrate

```sh
uv sync --locked
npm ci --prefix tools
uv run python -c "from mathtutor.settings import Settings; from mathtutor.store.db import upgrade; upgrade(Settings().database_url)"
```

The default database is `sqlite:///data/mathtutor.db`. The `upgrade()` helper creates its
parent directory and runs Alembic. The bare `alembic upgrade head` CLI needs the directory
to exist already; app construction does not create directories or run migrations. `data/` is ignored by git.
If overriding `MATHTUTOR_DATABASE_URL`, use the same URL for migration and app processes.
Do not use a production database for tests or local development.

## Start and exercise the app

```sh
uv run uvicorn mathtutor.web.app:app_factory --factory --port 8000
```

Open `http://127.0.0.1:8000/register`, create a local account, select a topic and practice.
Defaults use development cookies; production requires `MATHTUTOR_SECRET_KEY` (32+ chars).
In another terminal:

```sh
curl http://127.0.0.1:8000/readyz
npm exec --prefix tools -- playwright install chromium
npm run e2e --prefix tools
```

The smoke defaults to `http://127.0.0.1:8000`; override `BASE_URL` for another local port.
It registers a new account and changes practice state. CI installs Chromium with OS deps.
A passing `/readyz` checks content, database connectivity and pool liveness, not full schema
correctness: run migrations first even if connectivity succeeds.

## Focused checks

```sh
uv run python tools/check_docs.py
uv run pytest tests/unit/store tests/unit/application tests/integration/test_api.py -q
npm test --prefix tools
```

Use [app debugging](debugging/01-app.md) to narrow failures before running broader checks.
`npm run vendor --prefix tools` regenerates committed vendor assets/SRI; only run it when
intentionally updating those assets. [Security](security.md) explains CSP requirements.
