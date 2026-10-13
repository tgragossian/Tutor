# Task 1: Scaffold, docs check, CI

[Milestone A plan](../README.md) · [Constraints](../00-constraints.md)

**Files:**
- Create:
  - `pyproject.toml`, `.python-version` (`3.12`), `uv.lock`, `.gitattributes`
  - `src/mathtutor/__init__.py`
  - `tools/check_docs.py`
  - `tests/unit/test_smoke.py`, `tests/unit/test_check_docs.py`
  - `.github/workflows/ci.yml`
  - `docs/ops/README.md`, `docs/ops/hours.md`
- Modify:
  - `.gitignore`: add `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `dist/`, `node_modules/`, `test-results/`
  - `README.md`: add a "Development" section of ≤ 10 lines
  - `docs/README.md`: link `docs/ops/README.md`

**Interfaces:**
- Produces:
  - the importable package `mathtutor` (src layout), with `__version__ = "0.1.0"`
  - `tools/check_docs.py: def check(root: Path) -> list[str]`, which returns human-readable problems
  - the CI job `python`, which tasks 4 and 7 extend with sibling jobs

**Human prerequisites (Thomas):**
- Install uv: `winget install astral-sh.uv`, then reopen the terminal.
- After step 9, create a GitHub repository (public is recommended for the portfolio) and push `main`. CI must go green.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_smoke.py
def test_package_imports():
    import mathtutor
    assert mathtutor.__version__ == "0.1.0"

# tests/unit/test_check_docs.py  (helper: write(tmp_path, "a.md", text))
def test_too_long_file_reported(tmp_path):
    write(tmp_path, "a.md", "x\n" * 101)
    assert any("a.md" in p and "101 lines" in p for p in check(tmp_path))

def test_broken_relative_link_reported(tmp_path):
    write(tmp_path, "a.md", "[b](missing.md)\n")
    assert any("missing.md" in p for p in check(tmp_path))

def test_anchor_http_and_fenced_links_ok(tmp_path):
    write(tmp_path, "b.md", "# B\n")
    write(tmp_path, "a.md", "[b](b.md#b) [w](https://x.org) `[c](no2.md)`\n```\n[no](nope.md)\n```\n")
    assert check(tmp_path) == []

def test_excluded_dirs_skipped(tmp_path):
    write(tmp_path, "node_modules/x.md", "x\n" * 500)
    assert check(tmp_path) == []
```

- [ ] **Step 2:** Run `uv run pytest -q`. Expected: FAIL. No project exists yet, so uv reports a missing `pyproject.toml`.

- [ ] **Step 3: Create `pyproject.toml`.**
  - Build backend: hatchling. Package at `src/mathtutor`.
  - `requires-python = ">=3.12,<3.13"`.
  - Runtime dependencies: `fastapi`, `uvicorn[standard]`, `jinja2`, `pydantic>=2.7`, `pydantic-settings`.
  - Dev group: `pytest`, `httpx`, `ruff`, `mypy`.
  - ruff: line length 100, rules `E,F,I,B,UP`.
  - mypy: `strict = true` for `mathtutor.domain` and `mathtutor.content.*`; plain mypy elsewhere.
  - pytest: `testpaths = ["tests"]`.
  - Then run `uv sync`.

- [ ] **Step 4: Implement `check(root: Path) -> list[str]` in `tools/check_docs.py`.**
  - Walk `*.md` files. Skip `.git`, `.venv`, `node_modules`, `.superpowers` and `test-results`.
  - Flag any file over 100 lines.
  - Flag relative Markdown links whose target file is missing. Links inside fenced code blocks or inline code spans don't count.
  - Strip any `#anchor` before checking; ignore `http(s):` and `mailto:` links.
  - `main()` prints each problem and exits 1 if there are any.

- [ ] **Step 5:** Run `uv run pytest -q`, then `uv run python tools/check_docs.py`.
  - Expected: tests PASS, and the checker prints nothing for the current repo.
  - If an existing doc fails, fix the doc (split it or fix the link), never the checker.

- [ ] **Step 6: Line endings.**
  - `.gitattributes`: `* text=auto eol=lf`, plus `*.png binary` and `*.ico binary`.
  - Run `git add --renormalize .` and check `git status` shows only line-ending changes.

- [ ] **Step 7: CI.**
  - `ci.yml` runs on push and pull_request.
  - Job `python` on ubuntu-latest: `astral-sh/setup-uv` → `uv sync --locked` → `uv run ruff check .` → `uv run ruff format --check .` → `uv run mypy src` → `uv run pytest -q` → `uv run python tools/check_docs.py`.

- [ ] **Step 8: Docs.**
  - `README.md` "Development" section: install uv, `uv sync`, `uv run pytest`.
  - `docs/ops/README.md`: an index linking `hours.md`. Later tasks add more.
  - `docs/ops/hours.md`: a table with columns task | planned h | actual h | notes. Pre-fill the planned hours: 2, 3, 2, 3, 3, 2, 3, 2 (20 total).

- [ ] **Step 9: Verify everything.**
  - Run `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest -q`.
  - Expected: all pass.

- [ ] **Step 10: Commit** with the message `chore: scaffold package, docs check, CI`.
  - The line-ending renormalisation goes in a separate, earlier commit: `chore: normalize line endings to LF`.
