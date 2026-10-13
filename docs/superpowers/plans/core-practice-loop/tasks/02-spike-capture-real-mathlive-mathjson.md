[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 128–183. Review findings remain unresolved.

### Task 2: Spike — capture real MathLive MathJSON

This task decides which MathLive version is pinned and produces the fixtures the translator is built against (spec §12, risk 1). The capture is scripted so it can be rerun whenever the version changes.

**Files:**
- Create: `tools/mathlive_capture/index.html`, `tools/mathlive_capture/capture.py`, `tests/fixtures/mathjson/captured.json`, `tests/fixtures/mathjson/__init__.py` (helper), `tests/test_fixtures.py`, `docs/decisions/0001-mathlive-mathjson.md`

**Interfaces:**
- Produces: `tests/fixtures/mathjson/__init__.py: def mj(key: str) -> Any` returns captured MathJSON; `def latex(key: str) -> str`. All later verifier tests use these keys.

`captured.json` maps each key to `{"latex": str, "mathjson": Any}` for exactly these keys (key → LaTeX passed to `mf.setValue`):

| key | latex | key | latex |
|---|---|---|---|
| num_3 | `3` | sin2x | `\sin^2 x` |
| dec_0785 | `0.785` | sin_of_2x | `\sin(2x)` |
| dec_079 | `0.79` | arcsin | `\arcsin x` |
| dec_0780 | `0.780` | sin_inv | `\sin^{-1} x` |
| frac_pi_4 | `\frac{\pi}{4}` | abs_x | `\lvert x\rvert` |
| neg_half | `-\frac{1}{2}` | sqrt_x2 | `\sqrt{x^2}` |
| x2_sinx | `x^2\sin x` | ln_x2 | `\ln(x^2)` |
| d_x2sinx | `2x\sin x+x^2\cos x` | two_ln_x | `2\ln x` |
| d_x2sinx_wrong_sign | `2x\sin x-x^2\cos x` | x_plain | `x` |
| six_x_cos | `6x\cos(3x^2)` | inf | `\infty` |
| cos3x2 | `\cos(3x^2)` | neg_inf | `-\infty` |
| sqrt_x | `\sqrt{x}` | dne | `\mathrm{DNE}` |
| cuberoot | `\sqrt[3]{x}` | set_pts | `-1,1` |
| ln_abs_x | `\ln\lvert x\rvert` | implicit_ans | `-\frac{x}{y}` |
| ln_x | `\ln x` | implicit_alt | `-\frac{x}{\sqrt{25-x^2}}` |
| log_x | `\log x` | antideriv_c | `\frac{x^3}{3}+C` |
| log2_x | `\log_2 x` | antideriv | `\frac{x^3}{3}` |
| exp_x2 | `e^{x^2}` | antideriv_5 | `\frac{x^3}{3}+5` |
| exp_fn | `\exp(x)` | product_rule | `f'(x)g(x)+f(x)g'(x)` |
| sec2 | `\sec^2 x` | huge_pow | `10^{10^{10}}` |
| pi_e | `\pi+e` | incomplete | `x^{\placeholder{}}` |
| implicit_mult | `2\pi x` | matrix | `\begin{pmatrix}1&2\end{pmatrix}` |
| empty | *(empty string)* | | |

- [ ] **Step 1: Write the failing test** in `tests/test_fixtures.py`: every key above is present, and each entry has `latex` and `mathjson` keys.
- [ ] **Step 2:** Run `uv run pytest tests/test_fixtures.py -v`. Expected: FAIL (file missing).
- [ ] **Step 3: Build the capture page.**
  - `index.html` loads a pinned MathLive version. If needed for MathJSON, it also loads a pinned `@cortex-js/compute-engine`; pick versions released ≥ 2 weeks ago.
  - `capture.py` (Playwright, Python) opens the page and, for each key, calls `mf.setValue(latex)` then reads `mf.getValue('math-json')`. It writes `captured.json` with keys sorted.
  - **Configure MathLive for non-canonical output** (`ce.canonical = false`, or the equivalent per-call option) so `x^2\sin x` is not rewritten.
  - Record what canonical vs non-canonical output looks like in the ADR.
- [ ] **Step 4:** Run `uv run python tools/mathlive_capture/capture.py`, then `uv run pytest tests/test_fixtures.py -v`. Expected: PASS.
- [ ] **Step 5: Write ADR `0001`.** It records:
  - pinned versions + SRI hashes
  - how numbers appear (JSON number vs `{"num": "..."}`)
  - how primes, `Error`/placeholder, `\mathrm{DNE}`, lists and absolute value are encoded

  **Decision rule:** if MathJSON cannot represent the captured inputs faithfully, the ADR records the switch to the fallback (a restricted LaTeX grammar via `lark`), and Task 3 consumes LaTeX instead. Either way, the Task 3 interface is unchanged.
- [ ] **Step 6: Commit** `spike: capture MathLive MathJSON fixtures; ADR 0001`.

---

<!-- End preserved source. -->
