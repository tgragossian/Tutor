# Task 2: Spike — capture MathLive input; ADR 0002

[Milestone A plan](../README.md) · [Spec 02](../../../../specs/2026-10-13-portfolio-core/02-answer-contracts.md) · [Spec 03](../../../../specs/2026-10-13-portfolio-core/03-input-bounds.md)

This settles the questions in [01-foundation](../../01-foundation.md#decisions-the-spike-must-settle) using real browser output. The translator in milestone B is built against these fixtures.

**Files:**
- Create:
  - `tools/package.json`, `tools/package-lock.json`
  - `tools/capture/page.html`, `tools/capture/capture.mjs`, `tools/capture/cases.json`
  - `tests/fixtures/mathjson/captured.json`
  - `tests/support/__init__.py`, `tests/support/mathjson.py`
  - `tests/unit/test_captured_fixtures.py`
  - `docs/decisions/0002-mathlive-input.md`
- Modify: `docs/decisions/README.md` (link ADR 0002)

**Interfaces:**
- Produces:
  - `tests/support/mathjson.py`:
    - `def mj(key: str) -> Any`: the non-canonical MathJSON
    - `def latex(key: str) -> str`: `latex_out`
    - `def meta() -> dict[str, str]`
  - `captured.json` is `{"meta": {"mathlive": V, "compute_engine": V, "chromium": V}, "cases": {key: {...}}}`. Each case is `{"input": {"latex": s} | {"keys": [...]}, "latex_out": s, "mathjson": t, "mathjson_canonical": t}`.

**Cases (`tools/capture/cases.json`):** every case is set with `mf.setValue(latex)` unless marked typed.

```text
num_3 3 · neg_half -\frac{1}{2} · frac_pi_4 \frac{\pi}{4} · pi_e \pi+e
dec_0785 0.785 · dec_079 0.79 · dec_0780 0.780 · dec_inside \frac{0.5}{x}
x_plain x · implicit_mult 2\pi x · x2_sinx x^2\sin x · six_x_cos 6x\cos(3x^2)
sin2x \sin^2 x · sin_of_2x \sin(2x) · sec2 \sec^2 x · tan_x \tan x · cot_x \cot x
arcsin \arcsin x · sin_inv \sin^{-1} x · sqrt_x \sqrt{x} · cuberoot \sqrt[3]{x}
sqrt_x2 \sqrt{x^2} · abs_x \lvert x\rvert · ln_x \ln x · ln_x2 \ln(x^2)
log_x \log x · log2_x \log_2 x · exp_x2 e^{x^2} · exp_fn \exp(x)
rational_fn \frac{x^2-1}{x-1} · neg_power x^{-2} · frac_power x^{\frac{3}{2}}
huge_pow 10^{10^{10}} · long_int 1234567890123456789012345678901234567890
antideriv_c \frac{x^3}{3}+C · product_rule f'(x)g(x)+f(x)g'(x) · f_of_2x f(2x)
inf \infty · dne \mathrm{DNE} · set_pts -1,1
empty (empty) · incomplete x^{\placeholder{}} · matrix \begin{pmatrix}1&2\end{pmatrix}
typed_sin   keys: s i n ( 2 x )         typed_pow   keys: x ^ 2 ArrowRight + 1
typed_sqrt  keys: s q r t x             typed_frac  keys: 1 / x
```

**Version choice:**
- Use the newest `mathlive` (at least 0.111.1) and the `@cortex-js/compute-engine` version that MathLive's own `package.json` declares, plus `playwright` and `yaml`, all pinned exactly.
- The usual "two weeks old" rule doesn't apply to 0.111.1, because it contains security fixes. Note this in the ADR.

- [ ] **Step 1: Write the failing tests** in `test_captured_fixtures.py`.
  - Every key in `cases.json` is in `captured.json`, and every case has all four fields.
  - `meta()["mathlive"]` equals the exact version in `tools/package.json`, and so does `meta()["compute_engine"]`.
  - No version in `tools/package.json` dependencies contains `^`, `~`, `>`, `<`, `*` or `x`.
  - `mj("x_plain")` is not `None`, and `latex("x_plain") == "x"`.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_captured_fixtures.py -q`. Expected: FAIL (the fixture file is missing).
- [ ] **Step 3: Build the capture.**
  - `page.html` loads MathLive and Compute Engine from `node_modules` as ES modules and contains one `<math-field>`.
  - `capture.mjs`:
    - Starts a localhost static server rooted at `tools/` and launches Playwright Chromium.
    - For each case: set it, or focus the field and type it; then read `mf.getValue()`.
    - Parse the result twice, once with `canonical: false` and once canonical.
    - Write `captured.json` with keys sorted, 2-space indent and a trailing newline.
  - Add the npm scripts `capture` and `test` (`node --test`).
- [ ] **Step 4:** Run `npm ci --prefix tools`, `npx --prefix tools playwright install chromium`, `npm run capture --prefix tools`, then the pytest command from step 2. Expected: PASS.
- [ ] **Step 5: Write ADR 0002.** It must answer each item with evidence copied from `captured.json`:
  1. Pinned versions, and the exact parse call and option name used for non-canonical output.
  2. Number encoding. Does `dec_0780` keep its trailing zero? Choose spec 02's primary rule or its fallback, and say which.
  3. The head names for every allowed construct in spec 03's allowlist, including how `sin_inv`, `log2_x`, `cuberoot` and `abs_x` appear.
  4. How `empty`, `incomplete`, `matrix`, `huge_pow` and `long_int` look. These map to the format-issue codes.
  5. Whether typed input differs from `setValue` input. If it does, real browser captures (typed) are the ground truth for evaluation.
  6. `f_of_2x`, `product_rule` and `antideriv_c`, recorded for the deferred kinds.
  7. **Decision:** MathJSON is sufficient, so no custom LaTeX parser is needed. If it isn't, **stop and tell Thomas**: a custom parser contradicts spec 01 and needs a spec change, not a silent fallback.
- [ ] **Step 6: Human gate.** Thomas reads ADR 0002 and approves it before task 3 starts.
- [ ] **Step 7: Commit** with the message `spike: capture MathLive/Compute Engine input; ADR 0002`.
