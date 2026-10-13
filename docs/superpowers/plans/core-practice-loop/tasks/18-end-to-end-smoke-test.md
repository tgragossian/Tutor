[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 855–878. Review findings remain unresolved.

### Task 18: End-to-end smoke test

**Files:**
- Create: `tests/e2e/conftest.py` (starts uvicorn on a free port with a temp DB and `secure_cookies=False`), `tests/e2e/test_smoke.py`
- Modify: `ci.yml`. Add an e2e job: `uv run playwright install --with-deps chromium && uv run pytest -m e2e`.

**Interfaces:**
- Consumes: the running app.

- [ ] **Step 1: Write the test.**

```python
@pytest.mark.e2e
def test_practice_smoke(page, live_server):
    # register → setup (practice, 1 topic, skip warm-up) → item page
    # type the seed problem's correct answer via page.locator("math-field").type(...)
    # click Check → expect text "Correct"
```

- [ ] **Step 2:** Run `uv run pytest -m e2e -v`. Expected: FAIL before the conftest exists; PASS after.
- [ ] **Step 3: Commit** `test: Playwright end-to-end practice smoke test`.

---

<!-- End preserved source. -->
