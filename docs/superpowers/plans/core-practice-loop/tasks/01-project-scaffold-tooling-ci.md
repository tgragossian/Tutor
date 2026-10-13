[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 103–127. Review findings remain unresolved.

### Task 1: Project scaffold, tooling, CI

**Files:**
- Create: `pyproject.toml`, `.python-version` (3.12), `src/mathtutor/__init__.py` (`__version__ = "0.1.0"`), `tests/test_smoke.py`, `.github/workflows/ci.yml`
- Modify: `.gitignore`. Add `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `dist/`, `test-results/`

**Interfaces:**
- Produces: an importable `mathtutor` package (src layout) and the CI workflow that later tasks extend.

- [ ] **Step 1: Write the failing test**

```python
def test_package_imports():
    import mathtutor
    assert mathtutor.__version__ == "0.1.0"
```

- [ ] **Step 2:** Run `uv run pytest tests/test_smoke.py -v`. Expected: FAIL (no project / module).
- [ ] **Step 3: Create `pyproject.toml`.** Build with hatchling. Runtime deps: fastapi, uvicorn[standard], jinja2, python-multipart, pydantic, pydantic-settings, pyyaml, sympy, mpmath, sqlalchemy, alembic, argon2-cffi, itsdangerous, structlog. Dev group: pytest, hypothesis, pytest-playwright, httpx, ruff, mypy, types-PyYAML. Configure ruff (line length 100), mypy strict for the four pure packages, and `pytest` with `testpaths=["tests"]` and `-m "not e2e"` by default. Run `uv sync`.
- [ ] **Step 4:** Run `uv run pytest -v && uv run ruff check . && uv run mypy src`. Expected: all pass.
- [ ] **Step 5: CI.** In `ci.yml`: on push/PR, ubuntu-latest, `astral-sh/setup-uv`, `uv sync`, then ruff check, ruff format --check, mypy, pytest.
- [ ] **Step 6: Commit** `chore: scaffold package, tooling, CI`.

---

<!-- End preserved source. -->
