# Milestone A — File map

[Milestone A plan](README.md)

This follows the [structure review](../../../../reviews/2026-10-13/structure.md). Only what milestone A needs is created; no empty packages are made for later milestones.

```text
pyproject.toml, uv.lock, .python-version, .gitattributes      task 1
.github/workflows/ci.yml          python job (1), node job (4), container job (7)
src/mathtutor/
  __init__.py                     __version__                           task 1
  domain.py                       StrEnums shared by all layers         task 3
  settings.py                     Settings (pydantic-settings)          task 6
  content/
    schema.py                     compiled-content pydantic models      task 3
    loader.py                     load_bundle, content_version          task 4
  web/
    schemas.py                    SubmissionRequest, PublicItem         task 3
    app.py                        create_app, app_factory               task 6
    templates/base.html, index.html                                     task 6
tools/
  check_docs.py                   Markdown length + link checker        task 1
  package.json, package-lock.json pinned Node deps                      task 2
  capture/page.html, capture.mjs, cases.json                            task 2
  compile_content/compile.mjs, compile.test.mjs                         task 4
content/
  topics.yaml                                                           task 4
  problems/*.yaml                 six seed problems                     task 5
  compiled/problems.json          generated + committed                 tasks 4–5
  sources/openstax-calculus-v1.md licence + attribution manifest        task 5
contracts/
  README.md, examples/*.json      shared API payload examples           task 3
tests/
  unit/                           smoke, check_docs, fixtures, schemas, loader, seeds
  integration/test_app.py                                               task 6
  container/smoke.sh                                                    task 7
  fixtures/mathjson/captured.json                                       task 2
  fixtures/content/               small YAML + compiled bundles          task 4
  support/mathjson.py             mj(key), latex(key)                   task 2
Dockerfile, .dockerignore                                               task 7
deploy/compose.yaml, Caddyfile, .env.example, bootstrap.sh              tasks 7–8
docs/decisions/0002-mathlive-input.md                                   task 2
docs/ops/README.md, hours.md, local.md, host.md, runbook.md             tasks 1, 7, 8
```

## Responsibilities and dependency rules

- **`domain.py`:** standard-library `StrEnum`s only, with no framework imports. Every other layer imports from it.
- **`content/`:** depends on `domain` and pydantic. It never imports `web`.
- **`web/`:** depends on `content`, `domain` and `settings`.
  - `schemas.py` holds the HTTP contract.
  - `app.py` builds the app inside `create_app(settings)`. Nothing happens when the module is imported.
- **`tools/`:**
  - Node tools produce committed artefacts: fixtures and compiled content.
  - `check_docs.py` is standard-library Python.
- **`contracts/examples/`** are the payloads both the API tests (task 3) and the milestone B browser tests use.
