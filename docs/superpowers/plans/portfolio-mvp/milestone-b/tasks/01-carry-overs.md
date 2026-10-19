# Task 1: Milestone A carry-overs and exact decimals

[Milestone B plan](../README.md) · [Constraints](../00-constraints.md)

**Status (2026-10-19):** Complete: b03faac..813597c; R7 replaces the environment default; 4138181 tightens `loads_exact`.
See [rulings](../02-execution-rulings.md) and [execution status](../03-execution-status.md); checked steps include recorded replacements.

Closes the minors deferred from milestone A's final review and adds the exact-decimal reader every later task uses.

**Files:**
- Create: `src/mathtutor/jsonio.py`, `tests/unit/test_jsonio.py`
- Modify:
  - `src/mathtutor/content/loader.py`, `tests/unit/test_content_loader.py`
  - `src/mathtutor/web/app.py`, `tests/integration/test_app.py`
  - `deploy/compose.yaml`, `deploy/bootstrap.sh`, `deploy/.env.example`, `tests/container/smoke.sh`
  - `.github/workflows/ci.yml`, `docs/ops/runbook.md`, `README.md`

**Interfaces:**
- Produces:
  - `def as_num(literal: str) -> dict[str, str]` returns `{"num": literal}`
  - `def loads_exact(data: str | bytes) -> Any` = `json.loads(data, parse_float=as_num)`

- [x] **Step 1: Write the failing tests.**

```python
def test_decimal_becomes_num_literal(): assert loads_exact('[0.1, 2.675, 3]') == [{"num": "0.1"}, {"num": "2.675"}, 3]
def test_long_decimal_kept_verbatim(): s = "0." + "1" * 29; assert loads_exact(f"[{s}]") == [{"num": s}]
def test_exponent_literal_kept(): assert loads_exact("1.5e+3") == {"num": "1.5e+3"}
def test_loader_reads_mathjson_exactly(tmp_path): ...   # bundle with answer mathjson 0.785 → {"num": "0.785"}
def test_loader_problems_null_is_content_error(tmp_path): ...      # "problems": null → ContentError naming (root)
def test_loader_problems_missing_is_content_error(tmp_path): ...
def test_loader_duplicate_topic_id_or_order(tmp_path): ...         # ContentError "topics[1]: topic_id: duplicate"
def test_security_headers_on_500(): ...   # route that raises → 500 still has content-security-policy
```

- [x] **Step 2:** Run `uv run pytest tests/unit/test_jsonio.py tests/unit/test_content_loader.py tests/integration/test_app.py -q`. Expected: the new tests FAIL.
- [x] **Step 3: Implement.**
  - `jsonio.py` as above.
  - `load_bundle` reads with `loads_exact`; validates `problems` is a list and `topics` is a list with unique `topic_id` and `order`, each failure one `ContentError` line.
  - `content_version` values change once, because the hashed dict now holds `{"num": ...}` where it held a float; note the new bundle version in the commit body. No attempts exist yet, so nothing is orphaned.
  - Security headers: replace the `@app.middleware("http")` function with a pure ASGI middleware class that adds headers in `send` for `http.response.start`, so error responses get them too.
- [x] **Step 4: Ops carry-overs** (no tests beyond CI):
  - `compose.yaml`: `logging: {driver: json-file, options: {max-size: "10m", max-file: "3"}}` on both services.
  - `runbook.md`: add `sudo docker image prune -f` after `up -d` in "Update", and one line under a new "Costs" heading: "The AWS Budget alert emails at $10/month; it is not a spending cap."
  - `README.md`: one line linking `docs/ops/host.md` with the same not-a-cap wording.
  - `ci.yml`: `astral-sh/setup-uv@v5` gets `with: {version: "0.13.0"}`.
  - `smoke.sh`: the no-secret run uses `--name "$NAME-nosecret"`; `cleanup` removes it.
  - `bootstrap.sh`: run `mkswap /swapfile` unless `blkid /swapfile | grep -q 'TYPE="swap"'`.
  - `.env.example`: `SITE_ADDRESS=` empty, comment "e.g. localhost locally, your domain on the server", so compose's `:?` guard fails loudly.
- [x] **Step 5:** Run `uv run pytest -q && uv run mypy src && uv run ruff check . && uv run python tools/check_docs.py`. Expected: PASS.
- [x] **Step 6: Commit** `chore: milestone A carry-overs; exact decimal JSON reader`.
