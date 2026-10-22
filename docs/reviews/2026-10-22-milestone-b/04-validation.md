# Review validation and reproduction guide

[Review](README.md) · [Covered areas](05-covered-areas.md)

Date: 2026-10-22. Checkout: `main` **15169a2**, identical to `milestone-b`.
Platform: Windows, repository Python 3.12 environment. Production code/content unchanged.

## Fresh existing checks

| Command | Observed result |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | 890 passed, 1 skipped, 2 warnings; 148.48 s |
| `npm test --prefix tools` | 19 passed |
| `npm run compile --prefix tools` | Success; `git diff --exit-code -- content/compiled` clean |
| `.venv/Scripts/python.exe -m ruff check src tests tools migrations` | Passed |
| `.venv/Scripts/python.exe -m ruff format --check src tests tools migrations` | 88 files already formatted |
| `.venv/Scripts/python.exe -m mypy src` | Passed, 38 source files |
| `.venv/Scripts/python.exe -m mathtutor.verify.content_check` | Passed, 22 problems |
| `.venv/Scripts/python.exe -m mathtutor.verify.evaluate --set generated --gate B` | Passed: FA 0/84, FR 0/10, coverage 10/10, agreement 94/94 |
| `.venv/Scripts/python.exe -m mathtutor.verify.evaluate --set dev --gate B` | Passed: FA 0/50, FR 0/49, coverage 49/49, agreement 136/136 |

Both CLI sets had no internal errors. Dev unsupported accepted: 0/37.
Set SHA prefixes: dev `9a24709cb6f9`, generated `b8834cb3e5b6`.
The local verifier reports `0.1.0+dev` because no release SHA environment was supplied.
These reruns did not overwrite the published, SHA-tagged result artifacts.

The initial sandboxed pytest attempt could not access its temporary directory and was stopped;
an approved rerun produced the full result above. Remaining warnings: existing Starlette/httpx
deprecation and inaccessible pytest cache. The skipped test is Linux memory containment.
Node dependencies were installed with `npm ci --prefix tools --ignore-scripts`; lockfile unchanged.

## New probes (expected to fail before fixes)

From the repository/worktree root:

```sh
uv run pytest docs/reviews/2026-10-22-milestone-b/repro_state.py -q -p no:cacheprovider
uv run pytest docs/reviews/2026-10-22-milestone-b/repro_reservation.py -q -p no:cacheprovider
uv run pytest docs/reviews/2026-10-22-milestone-b/repro_load.py -q -p no:cacheprovider
node --test docs/reviews/2026-10-22-milestone-b/repro_ui.mjs
```

| Probe | Observation |
|---|---|
| `test_br5_*` | Alice's result references Bob's UUID after a busy duplicate deletes the reused row |
| `test_br2_*` | A newer-revision orphan replay applies normally; expected `StaleItem` is absent |
| `test_br3_*` | `seconds_on_item` is 49 instead of 42 after 7 seconds of simulated grading |
| `test_br4_*` | 16 `database_busy` replies produce `unexpected == 0` |
| Node B-R1 | Edited `2x` is visible, but the next request sends old `x` |

Observed: state/load run **3 failed** in 4.32 s; reservation run **1 failed** in 3.64 s;
Node controller run **1 failed**. Assertions fail on the described behavior, not setup errors.
Python probes use temporary SQLite databases; the UI probe executes the real controller
with DOM/parser/transport stubs. Their scope is explicit in each finding.

## Limits

No fresh Playwright/browser, Docker, Linux memory-limit, remote CI or production test was run.
Historical CI/host evidence remains linked in the [milestone evidence](../../superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md).
Passing dev/generated gates is regression evidence, not a held-out accuracy estimate or a
new proof of general symbolic soundness. This pass is not a vendor dependency security audit.

Documentation validation: `python tools/check_docs.py` and `git diff --check` passed after edits.
Repository-wide ruff lint/format checks include the new probes. All new review children link
to the review index; every Markdown file passes the 100-line limit and local-link checks.
