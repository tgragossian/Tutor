[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 826–854. Review findings remain unresolved.

### Task 17: Pages and MathLive UI

**Files:**
- Create: `src/mathtutor/web/pages.py`, `templates/{base,login,register,dashboard,setup,item,report}.html`, `static/app.js`, `static/app.css`, `static/vendor/` (the MathLive and compute-engine files pinned in ADR 0001, plus `htmx.min.js` 2.x pinned, each with SRI in `base.html`), `tests/web/test_pages.py`

**Interfaces:**
- Consumes: the API from Task 16.
- Pages follow §7.1. Templates call the JSON API through HTMX or `fetch` in `app.js`, so pages hold no logic of their own.
- **Calculus button row:** `a/b`, `xⁿ`, `√`, `sin`, `cos`, `tan`, `ln`, `eˣ`, `π`, `|x|`, `∞`, `+C`, **`DNE`** (inserts `\mathrm{DNE}`). Each inserts with `mf.executeCommand(['insert', …])`, as in the approved mockup. The built-in virtual keyboard is set to `math-virtual-keyboard-policy="auto"`.
- **Precision hint text:**
  - `decimals = N` → "Enter an exact value, or a decimal rounded to N places"
  - `decimals = null` → "Exact answer required"
- **Formula-sheet panel:** rendered from `bank.formula_items(topic)` and shown only when the exam conditions allow it.
- **Copy:** verdict text exactly as in §4.5; format issues show their `message`.

- [ ] **Step 1: Write the failing tests** (`TestClient` HTML assertions):
  - `/` redirects to `/login` when logged out
  - the dashboard lists all 15 topic names
  - the setup page has the four modes/conditions controls
  - the item page contains a `math-field` element, all 13 buttons, and the correct precision hint for a `decimals=2` problem
  - the formula panel is absent under `closed_book` and present under `formula_sheet`
  - script tags for vendor files carry `integrity=`
- [ ] **Step 2:** Run `uv run pytest tests/web/test_pages.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement. Keep the CSS minimal and readable.
- [ ] **Step 4:** Rerun the tests. Expected: PASS. Then run `uv run uvicorn mathtutor.web.app:app --reload` (export `app = create_app(Settings())` for dev) and click through one practice session by hand.
- [ ] **Step 5: Commit** `feat(web): pages, MathLive input with calculus keyboard`.

---

<!-- End preserved source. -->
