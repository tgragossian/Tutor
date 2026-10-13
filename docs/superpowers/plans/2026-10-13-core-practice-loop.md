# Core Practice Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy sub-project 1 of the adaptive Calculus tutor. Students sign up, run diagnostic, practice or recap sessions on 15 Calc I topics, enter answers with MathLive, and get verdicts from a sandboxed, measured SymPy verifier.

**Architecture:** One FastAPI app that serves both server-rendered pages (Jinja + HTMX) and a JSON API.
- **Pure core:** `verify`, `mastery` and `recommend` touch neither the database nor the web.
- **Content:** version-controlled YAML, validated at startup.
- **User data:** SQLite (SQLAlchemy + Alembic).
- **Hosting:** Docker on Lightsail behind Caddy, with nightly backups to S3.

**Tech Stack:** Python 3.12, uv, FastAPI, Jinja2, HTMX, MathLive, pydantic v2, pydantic-settings, SymPy, mpmath, SQLAlchemy 2.0, Alembic, argon2-cffi, structlog, pytest, Hypothesis, pytest-playwright, ruff, mypy, Docker, Caddy, GitHub Actions, AWS Lightsail + S3.

**Spec:** `docs/superpowers/specs/2026-10-13-core-practice-loop-design.md`. Read it first. Section numbers below (§) refer to it.

## Global Constraints

- Python **3.12**. Dependencies are managed with `uv`; every command runs via `uv run`.
- `sympify`, `parse_expr` and `eval` are **never** called on student input (§4.1). `parse_expr` is allowed only on trusted YAML content.
- Every variable symbol (`x`, `y`, `f`, `fp`, …) is created as `sympy.Symbol(name, real=True)`, in both `translate` and `parse_expected`, so both sides compare as the same symbols.
- **Numeric-point rule (refines spec §4.2):** a sample point is skipped only when the **expected** value is undefined, complex or non-finite there. If the expected value is defined and the student's is not, that point is a counterexample (reason `student_undefined`). Otherwise `2 ln x` would pass for `ln(x²)` just by skipping every negative point.
- Verdict statuses are exactly `correct | incorrect | unable_to_verify`. A parse or translation failure is never `incorrect`.
- The pure packages (`verify`, `mastery`, `recommend`, `content`) must not import `fastapi`, `sqlalchemy` or `mathtutor.web` / `mathtutor.store`.
- `mypy --strict` passes on `verify`, `mastery`, `recommend` and `content`. `ruff check` and `ruff format --check` pass everywhere.
- Only problems with `status` in `{human_verified, auto_verified, computed_only}` are served.
- Numbers fixed by the spec:

  | What | Value |
  |---|---|
  | Verifier timeout | 3 s |
  | Worker memory cap | 512 MB |
  | Input size limits | 200 nodes, depth 30, integer literals ≤ 30 digits, \|exponent literal\| ≤ 1000 |
  | Numeric check | 20 points, ≥ 10 valid, relative tolerance 1e-8, 50 digits |
  | Abstract-function symbols | sampled from [-3, 3] |
  | Default `decimals` | 3 |
  | Mastery formula | (Σw·c + 1)/(Σw + 2) |
  | Mastery bands | < 2 attempts → `not_seen`; < 0.5 `weak`; < 0.8 `shaky`; else `strong` |
  | Multiple-choice weight | 0.5 |
  | Recency decay | 0.5^(k/10) |
  | Minutes per difficulty 1–5 | 1.5 / 2.5 / 3.5 / 4.5 / 6; recall and concept items 0.5 |
  | Warm-up | ≤ 6 items |
  | Tries per problem | 3 (practice) |
  | Rate limits | auth 10/min per IP; attempts 30/min per user |
  | Usernames | `^[a-z0-9_]{3,32}$` |
  | Passwords | 8–128 characters |
  | Custom minutes | 5–180 |
  | S3 backups kept | 14 |
  | Budget alert | $10 |

- The secrets `SECRET_KEY` and `DATABASE_URL` come from environment variables. `.env` is never committed.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Domain-limited "identities."** Student `√(x²)` for expected `x`, and student `2 ln x` for expected `ln(x²)`, agree only on part of ℝ. On a domain that includes negatives both must be judged `incorrect`, never `correct`. *(Test in Task 4.)*
2. **Incomplete MathLive input.** An empty placeholder or an `Error` node (for example the student typed `x^` and stopped) must give a format message ("incomplete expression"). It must not be a verdict and must not create an attempt. *(Tests in Tasks 3 and 5.)*
3. **Sparse content.** 20 seed problems cover 15 topics, so practice will often find no problem at the target difficulty, or none unseen. The policy must fall back in this order: nearest difficulty → seen-but-incorrect → next weakest selected topic → `done` with a reason. It must never raise or loop. *(Test in Task 14.)*
4. **Time budget expires mid-problem.** A submission for the item already on screen is still graded, and `next` then returns `done`. *(Tests in Tasks 14 and 16.)*
5. **Double-submit after an item is finished** (a double-click, or a resubmit after "Show answer") must return `409`. It must not create a second attempt or shift mastery. *(Test in Task 16.)*

---

## File Structure

```
pyproject.toml, uv.lock, .python-version, .gitignore, README.md
.github/workflows/ci.yml, deploy.yml
docs/decisions/0001-mathlive-mathjson.md          # Task 2 result
tools/mathlive_capture/index.html, capture.py      # Task 2
src/mathtutor/
  __init__.py
  domain.py               # AttemptRecord, SessionPlan, shared Literals (Task 11)
  verify/
    types.py              # AnswerSpec, Verdict, FormatIssue, DNE (Task 3)
    translate.py          # MathJSON→SymPy allowlist (Task 3)
    expected.py           # parse_expected for trusted answers (Task 4)
    equivalence.py        # symbolic + numeric comparison (Task 4)
    checkers.py           # pre-checks + per-type check() (Task 5)
    implicit.py           # implicit_derivative (Task 6)
    sandbox.py            # VerifierPool (Task 7)
  content/
    models.py, loader.py  # Task 8
  mastery/scores.py       # Task 11
  recommend/
    base.py, budget.py, diagnostic.py, recap.py, baseline.py   # Task 13
    practice.py           # Task 14
  store/
    models.py, db.py, repo.py      # Task 12
  web/
    settings.py, app.py, auth.py, security.py, errors.py, logging.py  # Task 15
    api.py, flow.py       # Task 16
    pages.py, templates/*.html, static/{app.js, app.css, vendor/}     # Task 17
migrations/               # Alembic (Task 12)
content/topics.yaml, problems/*.yaml, formulas/*.yaml   # Tasks 8–9
eval/verifier_cases.yaml, generated_cases.yaml, generate_cases.py, run_verifier_eval.py, sympy_to_mathjson.py  # Task 10
tests/ (mirrors src), tests/fixtures/mathjson/captured.json, tests/e2e/
deploy/Dockerfile, docker-compose.yml, Caddyfile, backup.sh   # Task 19
```

---

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

### Task 3: Verifier types and MathJSON → SymPy translator

**Files:**
- Create: `src/mathtutor/verify/__init__.py`, `types.py`, `translate.py`, `tests/verify/test_translate.py`, `tests/verify/test_translate_properties.py`

**Interfaces:**
- Consumes: `mj()` (Task 2).
- Produces, in `verify/types.py`:

```python
AnswerType = Literal["numeric", "expression", "antiderivative", "limit",
                     "implicit_derivative", "point_set", "multiple_choice"]
Status = Literal["correct", "incorrect", "unable_to_verify"]
Method = Literal["symbolic", "numeric", "exact", "rounding", "none"]

@dataclass(frozen=True)
class AnswerSpec:
    answer_type: AnswerType
    answer: str | tuple[str, ...]          # tuple only for point_set
    variable: str = "x"
    sample_domain: tuple[float, float] = (-5.0, 5.0)
    decimals: int | None = 3
    choice_ids: tuple[str, ...] = ()
    relation: str | None = None
    functions: tuple[str, ...] = ()

@dataclass(frozen=True)
class Verdict:  # exactly as spec §4.5
    status: Status; reason: str; method: Method; latency_ms: int

@dataclass(frozen=True)
class FormatIssue:
    code: Literal["empty", "incomplete", "too_few_decimals", "exact_required"]
    message: str

class _Dne: ...          # singleton
DNE: Final = _Dne()
```

- Also produces, in `verify/translate.py`:
  - `class Rejected(Exception): reason: Literal["unsupported_notation", "input_too_large", "incomplete"]`
  - `def translate(mathjson: Any, *, symbols: frozenset[str], functions: frozenset[str] = frozenset()) -> sympy.Expr | _Dne | tuple[sympy.Expr, ...]`

  It implements exactly the §4.1 allowlist and limits. Function names map as follows:
  - `f(x)` → `Symbol("f")`
  - `f'(x)` → `Symbol("fp")`, likewise `g`/`gp`, only when listed in `functions`
  - `log x` → log base 10
  - `\sin^{-1}` → `asin`

- [ ] **Step 1: Write the failing tests**

```python
X = frozenset({"x"})
def test_product(): assert translate(mj("x2_sinx"), symbols=X) == x**2 * sp.sin(x)
def test_log_base10(): assert translate(mj("log_x"), symbols=X) == sp.log(x, 10)
def test_log_base2(): assert translate(mj("log2_x"), symbols=X) == sp.log(x, 2)
def test_inverse_sin_both_spellings():
    assert translate(mj("arcsin"), symbols=X) == translate(mj("sin_inv"), symbols=X) == sp.asin(x)
def test_sin_squared_vs_sin_of_2x():
    assert translate(mj("sin2x"), symbols=X) == sp.sin(x)**2
    assert translate(mj("sin_of_2x"), symbols=X) == sp.sin(2*x)
def test_infinities(): assert translate(mj("inf"), symbols=X) == sp.oo and translate(mj("neg_inf"), symbols=X) == -sp.oo
def test_dne(): assert translate(mj("dne"), symbols=X) is DNE
def test_point_list(): assert set(translate(mj("set_pts"), symbols=X)) == {-1, 1}
def test_abstract_functions():
    assert translate(mj("product_rule"), symbols=X, functions=frozenset({"f", "g"})) == fp*g + f*gp
def test_abstract_function_not_declared_rejected():
    with pytest.raises(Rejected) as e: translate(mj("product_rule"), symbols=X)
    assert e.value.reason == "unsupported_notation"
def test_unknown_symbol_rejected():          # y is not allowed unless passed
    with pytest.raises(Rejected): translate(mj("implicit_ans"), symbols=X)
def test_matrix_rejected(): ...              # reason == "unsupported_notation"
def test_huge_power_rejected(): ...          # reason == "input_too_large"
def test_incomplete_rejected(): ...          # mj("incomplete") → reason == "incomplete"  (Review Focus 2)
def test_depth_limit(): ...                  # 31 nested Negate → "input_too_large"
```

  In `test_translate_properties.py`, use Hypothesis to build recursive random trees from allowed heads, unknown heads, random strings and numbers. Assert that `translate` either returns a value or raises `Rejected`, and never raises anything else.

- [ ] **Step 2:** Run `uv run pytest tests/verify -v`. Expected: FAIL (import errors).
- [ ] **Step 3: Implement `types.py` and `translate.py`.**
  - Recursive descent over the captured encoding from ADR 0001, with a node counter and depth counter passed down.
  - Numbers become `sp.Integer` or `sp.Rational`; decimals use `sp.Rational(str)`, so decimals stay exact.
- [ ] **Step 4:** Run `uv run pytest tests/verify -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(verify): MathJSON allowlist translator`.

---

### Task 4: Trusted-answer parsing and equivalence core

**Files:**
- Create: `src/mathtutor/verify/expected.py`, `equivalence.py`, `tests/verify/test_expected.py`, `tests/verify/test_equivalence.py`

**Interfaces:**
- Produces:
  - `def parse_expected(spec: AnswerSpec) -> sympy.Expr | _Dne | tuple[sympy.Expr, ...]`
    - Uses `parse_expr` with `local_dict` holding only the spec's symbols, `fp`/`gp`, and SymPy functions.
    - Also recognises `oo`, `-oo` and `DNE`.
    - Raises `ValueError` with the offending string.
  - `def compare(student: sympy.Expr, expected: sympy.Expr, *, variable: str, domain: tuple[float, float], seed: int = 0) -> tuple[Status, str, Method]`
    - Implements §4.2 steps 1–2.
    - Free symbols other than `variable` are sampled from [-3, 3].
    - Reasons: `symbolic_equal`, `numeric_agree`, `counterexample`, `student_undefined`, `insufficient_sample_points`.
    - Step 1 goes through a private `_symbolic_equal(a, b) -> bool` (`simplify(a - b) == 0`), so tests can force the numeric path.
    - The numeric-point rule from Global Constraints applies.

- [ ] **Step 1: Write the failing tests**

```python
def test_symbolic_equal(): assert compare(sp.sin(x)**2 + sp.cos(x)**2, sp.Integer(1), variable="x", domain=(-5, 5))[0] == "correct"
def test_counterexample(): assert compare(2*x, x**2, variable="x", domain=(-5, 5)) == ("incorrect", "counterexample", "numeric")
def test_numeric_path_used_when_simplify_cant(monkeypatch):
    monkeypatch.setattr(equivalence, "_symbolic_equal", lambda a, b: False)
    assert compare(sp.sin(x)**2 + sp.cos(x)**2, sp.Integer(1), variable="x", domain=(-5, 5)) == ("correct", "numeric_agree", "numeric")
def test_sqrt_x2_not_x_on_mixed_domain():  # Review Focus 1
    assert compare(sp.sqrt(x**2), x, variable="x", domain=(-5, 5))[0] == "incorrect"
def test_student_undefined_where_expected_defined():  # Review Focus 1: student 2 ln x, expected ln(x²)
    assert compare(2*sp.log(x), sp.log(x**2), variable="x", domain=(-5, 5)) == ("incorrect", "student_undefined", "numeric")
def test_ln_x2_vs_2lnx_positive_domain(): assert compare(sp.log(x**2), 2*sp.log(x), variable="x", domain=(0.1, 5))[0] == "correct"
def test_insufficient_points():  # expected undefined on the whole domain
    assert compare(sp.sqrt(x - 10), sp.sqrt(x - 10) + 1, variable="x", domain=(-5, 5)) == ("unable_to_verify", "insufficient_sample_points", "none")
def test_abstract_symbols_sampled(): assert compare(fp*g + f*gp, gp*f + g*fp, variable="x", domain=(-5, 5))[0] == "correct"
def test_parse_expected_rejects_garbage(): pytest.raises(ValueError, parse_expected, AnswerSpec("expression", "6*x*cos(("))
def test_parse_expected_dne_and_oo(): ...
```

- [ ] **Step 2:** Run `uv run pytest tests/verify/test_expected.py tests/verify/test_equivalence.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Use `random.Random(seed)` to draw points and `mpmath.mp.dps = 50` (scoped with `mpmath.workdps(50)`).
  - Evaluate with `sp.lambdify(..., "mpmath")`.
  - A point is *expected-invalid*, and skipped, if evaluating the expected answer raises or gives a complex or non-finite value. If only the student's side fails there, that is `student_undefined`.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(verify): trusted parsing and equivalence`.

---

### Task 5: Pre-checks and per-type checkers

**Files:**
- Create: `src/mathtutor/verify/checkers.py`, `tests/verify/test_checkers.py`

**Interfaces:**
- Consumes: `translate`, `parse_expected`, `compare`.
- Produces: `def check(spec: AnswerSpec, mathjson: Any, latex: str) -> Verdict | FormatIssue`. It runs in process; Task 7 wraps it in the sandbox.
  - **Pre-checks run first, on `latex`:**
    - empty → `FormatIssue("empty")`
    - `Rejected("incomplete")` → `FormatIssue("incomplete")`
    - a bare decimal matching `^-?\d+\.(\d+)$` with fewer than `decimals` places → `too_few_decimals`
    - a decimal when `decimals is None` → `exact_required`

    Decimal places are counted from the LaTeX, because MathJSON may drop trailing zeros.
  - Any other `Rejected` → `Verdict("unable_to_verify", reason, "none", ms)`.
  - Then the §4.2 table for every type except `implicit_derivative`, which delegates to Task 6.
  - Rounding reasons: `rounding_match` / `rounding_mismatch` (method `rounding`).
  - `multiple_choice` uses `mathjson` as the choice id string, method `exact`.

- [ ] **Step 1: Write the failing tests** (spec values):

```python
NUM = AnswerSpec("numeric", "pi/4")
def test_decimal_rounds_3(): assert check(NUM, mj("dec_0785"), latex("dec_0785")).status == "correct"
def test_decimal_too_few_places(): assert check(NUM, mj("dec_079"), latex("dec_079")) == FormatIssue("too_few_decimals", ANY)
def test_decimal_trailing_zero_counts(): assert check(AnswerSpec("numeric", "0.78"), mj("dec_0780"), latex("dec_0780")).status == "correct"
def test_decimals_2_accepts_079(): assert check(AnswerSpec("numeric", "pi/4", decimals=2), mj("dec_079"), latex("dec_079")).status == "correct"
def test_exact_required(): assert isinstance(check(AnswerSpec("numeric", "pi/4", decimals=None), mj("dec_0785"), latex("dec_0785")), FormatIssue)
def test_exact_form(): assert check(NUM, mj("frac_pi_4"), latex("frac_pi_4")).method == "symbolic"
def test_expression_wrong_sign():
    s = AnswerSpec("expression", "2*x*sin(x) + x**2*cos(x)")
    assert check(s, mj("d_x2sinx_wrong_sign"), latex("d_x2sinx_wrong_sign")).status == "incorrect"
def test_antiderivative_any_constant():
    s = AnswerSpec("antiderivative", "x**3/3")
    for k in ("antideriv", "antideriv_c", "antideriv_5"): assert check(s, mj(k), latex(k)).status == "correct"
def test_antiderivative_ln_abs(): ...      # spec answer "log(x)", student ln|x| → correct on domain (0.1, 5) and on (-5, 5)
def test_limit_tokens(): ...               # oo vs mj("inf") correct; oo vs mj("neg_inf") incorrect; DNE vs mj("dne") correct; DNE vs mj("num_3") incorrect
def test_point_set_order_free(): assert check(AnswerSpec("point_set", ("1", "-1")), mj("set_pts"), latex("set_pts")).status == "correct"
def test_point_set_size_mismatch(): ...    # expected ("1",) → incorrect
def test_multiple_choice(): assert check(AnswerSpec("multiple_choice", "b", choice_ids=("a","b","c")), "b", "").status == "correct"
def test_empty(): assert check(NUM, mj("empty"), "") == FormatIssue("empty", ANY)
def test_incomplete_is_format_issue(): assert isinstance(check(NUM, mj("incomplete"), latex("incomplete")), FormatIssue)  # Review Focus 2
def test_unsupported_is_unable(): assert check(NUM, mj("matrix"), latex("matrix")).status == "unable_to_verify"
```

- [ ] **Step 2:** Run `uv run pytest tests/verify/test_checkers.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `check`.** The type dispatch is a dict of private functions. `latency_ms` is measured around the whole call.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(verify): pre-checks and answer-type checkers`.

---

### Task 6: Implicit-derivative checker

**Files:**
- Create: `src/mathtutor/verify/implicit.py`, `tests/verify/test_implicit.py`
- Modify: `checkers.py`. Route `implicit_derivative` here and pass `symbols={variable, "y"}`.

**Interfaces:**
- Produces: `def check_implicit(student: sympy.Expr, expected: sympy.Expr, relation: sympy.Expr, *, variable: str, domain: tuple[float, float], seed: int = 0) -> tuple[Status, str, Method]`.
  - For each of 20 x-values, find real y with `relation(x, y) = 0`: `sympy.nsolve` from starts y ∈ {-10, -1, 0.5, 1, 10}, deduplicated.
  - Compare at every (x, y) pair using the §4.2 tolerance.
  - With fewer than 10 valid pairs → `insufficient_sample_points`.

  **Algorithm note:** a student answer must match the expected answer **at each (x, y) pair it is defined at**. For the circle example, `-x/√(25−x²)` only matches on the upper branch. It is therefore judged `incorrect`, with a counterexample on the lower branch, unless the problem restricts the domain. Encode this explicitly in a test so it is a decision, not an accident.

- [ ] **Step 1: Write the failing tests**

```python
REL = x**2 + y**2 - 25
def test_equivalent_on_curve(): assert check_implicit(-x/y, -x/y, REL, variable="x", domain=(-4, 4))[0] == "correct"
def test_wrong_sign(): assert check_implicit(x/y, -x/y, REL, variable="x", domain=(-4, 4))[0] == "incorrect"
def test_explicit_branch_rejected_on_full_curve():
    assert check_implicit(-x/sp.sqrt(25 - x**2), -x/y, REL, variable="x", domain=(-4, 4))[0] == "incorrect"
def test_curve_dependent_form_accepted(): ...   # x**2+y**2=25: student (-x*y)/(25 - x**2) vs expected -x/y → correct (equal only on the curve)
def test_no_real_points(): ...                  # relation x**2+y**2+1 → ("unable_to_verify", "insufficient_sample_points", "none")
```

- [ ] **Step 2:** Run `uv run pytest tests/verify/test_implicit.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement**, and add one routing test in `test_checkers.py` that uses `mj("implicit_ans")` and `mj("implicit_alt")`.
- [ ] **Step 4:** Run `uv run pytest tests/verify -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(verify): implicit differentiation checker`.

---

### Task 7: Sandboxed verifier pool

**Files:**
- Create: `src/mathtutor/verify/sandbox.py`, `tests/verify/test_sandbox.py`, `tests/verify/slow_checks.py` (module-level `sleep_forever(spec, mj, latex)` and `explode(spec, mj, latex)` for spawn)

**Interfaces:**
- Produces: `class VerifierPool`
  - `__init__(self, size: int = 2, timeout_s: float = 3.0, memory_mb: int = 512, check_fn: Callable[[AnswerSpec, Any, str], Verdict | FormatIssue] = check)`
  - `check(self, spec: AnswerSpec, mathjson: Any, latex: str) -> Verdict | FormatIssue`
  - `close(self) -> None`
  - It is also a context manager.
- How it works:
  - Each worker is a `multiprocessing` spawn-context `Process` with a `Pipe`. Callers take a free worker from a `queue.Queue`.
  - On timeout, the worker is terminated, respawned, and the caller gets `Verdict("unable_to_verify", "timeout", "none", ms)`.
  - On a worker exception → `internal_error`, logged.
  - On Linux the worker calls `resource.setrlimit(RLIMIT_AS, memory_mb MB)` at startup.
  - The pool is thread-safe, because FastAPI calls it from its threadpool.

- [ ] **Step 1: Write the failing tests**

```python
def test_passthrough():
    with VerifierPool(size=1) as p: assert p.check(AnswerSpec("numeric", "3"), mj("num_3"), "3").status == "correct"
def test_timeout_then_recovers():
    with VerifierPool(size=1, timeout_s=0.5, check_fn=sleep_forever) as p:
        v = p.check(AnswerSpec("numeric", "3"), 3, "3"); assert (v.status, v.reason) == ("unable_to_verify", "timeout")
    # second call on a respawned worker with the real check succeeds:
    with VerifierPool(size=1) as p: assert p.check(AnswerSpec("numeric", "3"), mj("num_3"), "3").status == "correct"
def test_exception_is_internal_error(): ...      # explode → reason "internal_error"
def test_concurrent_calls(): ...                 # 8 threads, size=2 → all correct
```

- [ ] **Step 2:** Run `uv run pytest tests/verify/test_sandbox.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `VerifierPool` as described above.
- [ ] **Step 4:** Rerun the tests. Expected: PASS (on Windows the memory limit is skipped).
- [ ] **Step 5: Commit** `feat(verify): sandboxed verifier pool with timeout`.

---

### Task 8: Content schemas, loader, topics

**Files:**
- Create: `src/mathtutor/content/__init__.py`, `models.py`, `loader.py`, `content/topics.yaml` (all 15 topics, exactly as in the §3.1 table), `tests/content/test_loader.py`, `tests/content/fixtures/` (small valid and invalid content trees)

**Interfaces:**
- Consumes: `AnswerSpec`, `parse_expected`, `compare`.
- Produces:
  - pydantic models `Topic`, `Source`, `Choice`, `Problem`, `FormulaItem`, with the fields of §3.1–3.3. Each of `Problem` and `FormulaItem` has `.answer_spec() -> AnswerSpec`.
  - `ProblemStatus = Literal["human_verified", "auto_verified", "computed_only", "needs_review"]`
  - `SERVABLE: frozenset[ProblemStatus]`
  - `class ContentError(Exception)`
  - `@dataclass(frozen=True) class ContentBank`, with fields:
    - `topics: Mapping[str, Topic]`
    - `problems: Mapping[str, Problem]`
    - `formulas: Mapping[str, FormulaItem]`

    and methods:
    - `servable_problems(topic: str) -> list[Problem]`
    - `formula_items(topic: str) -> list[FormulaItem]`
    - `topic_of(item_id: str) -> str`
    - `item_version(item_id: str) -> str` (12 hex chars of the SHA-256 of the canonical JSON)
    - `is_problem(item_id) -> bool`
  - `def load_content(root: Path) -> ContentBank`
- Validation raises `ContentError`, naming the file and item, for:
  - a schema error
  - a duplicate id across problems and formulas
  - an unknown topic or prerequisite
  - a prerequisite cycle
  - `parse_expected` failure
  - the expected answer not judged `correct` against itself by `compare` (skipped for `multiple_choice`, `limit` tokens and `point_set` sizes)
  - `choices` present iff the type is `multiple_choice`
  - `relation` present iff the type is `implicit_derivative`

- [ ] **Step 1: Write the failing tests:** loading the real `content/` gives 15 topics in `order` 1..15; each invalid fixture raises `ContentError` with a matching message (`"cycle"`, `"unknown topic"`, `"duplicate id"`, `"cannot parse"`); `servable_problems` excludes `needs_review`; `item_version` is stable across reloads and changes when `answer` changes.
- [ ] **Step 2:** Run `uv run pytest tests/content -v`. Expected: FAIL.
- [ ] **Step 3:** Implement. Cycle check via DFS. Problem and formula files are `*.yaml` lists, loaded in sorted filename order.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(content): schemas, loader, topic graph`.

---

### Task 9: Seed content (developer-authored)

Most of this is your writing, not code. Tests define what "done" means.

**Files:**
- Create: `content/problems/*.yaml` (one file per area), `content/formulas/*.yaml`, `docs/content-authoring.md` (the §4.3 rubric, the field guide, and "facts not wording" for cheat sheets), `tests/content/test_seed_content.py`

**Interfaces:**
- Consumes: `load_content`.

- [ ] **Step 1: Write the failing tests:**
  - ≥ 20 problems, all `human_verified`
  - every topic has ≥ 1 problem
  - every `answer_type` is used ≥ 1 time
  - every topic has ≥ 5 `recall` and ≥ 2 `concept` items
  - every recall item has `memorize` set
  - each topic has ≥ 1 `core` recall item
  - every source `url` starts with `https://openstax.org/`, and `license == "CC BY-NC-SA 4.0"`
- [ ] **Step 2:** Run `uv run pytest tests/content/test_seed_content.py -v`. Expected: FAIL.
- [ ] **Step 3:** Author the content from OpenStax Vol. 1 using the rubric. `load_content` self-checks every expected answer.
- [ ] **Step 4:** Rerun the tests plus `uv run pytest tests/content -v`. Expected: PASS.
- [ ] **Step 5: Commit** `content: seed problems and formula/concept items for 15 topics`.

---

### Task 10: Verifier evaluation set and CI gate

**Files:**
- Create:
  - `eval/sympy_to_mathjson.py`: SymPy → MathJSON in the ADR-0001 encoding; used only for evaluation
  - `eval/generate_cases.py`
  - `eval/generated_cases.yaml` (committed output)
  - `eval/verifier_cases.yaml` (hand-written)
  - `eval/run_verifier_eval.py`
  - `tests/eval/test_eval_runner.py`
- Modify: `ci.yml`. Add the step `uv run python eval/run_verifier_eval.py --fail-on-false-accept`.

**Interfaces:**
- **Case format:** `{id, problem: <problem id> | inline AnswerSpec fields, student: {latex, mathjson}, label: correct | incorrect | unsupported, note}`.
- **Generator, per seed problem:**
  - correct variants that are guaranteed equal: `expand`, `factor`, `together`, `trigsimp` rewrites, + constants for antiderivatives
  - incorrect variants that are guaranteed different: negate, ×2, + 1 (non-antiderivative), drop the outermost chain factor, power ± 1

    A variant is kept only if SymPy proves `simplify(variant - expected) != 0` at a rational sample point. This label check is independent of the code under test.
- **Hand-written:** ≥ 80 cases covering every captured fixture key plus classic traps:
  - `sin^2 x` vs `sin(2x)`
  - `log` base confusion
  - `ln|x|`
  - decimal rounding
  - `DNE` vs `∞`
- **Runner:** `run_verifier_eval.py [--fail-on-false-accept] [--out eval/report.md]`. It runs each case through `VerifierPool` and prints a table by `answer_type` × `method` with:
  - FA rate (label incorrect, verdict correct)
  - FR rate (label correct, verdict incorrect)
  - inconclusive rate (label correct or incorrect, verdict unable)
  - `unsupported` handled rate
  - p50/p95 latency

  It exits 1 if FA > 0 under the flag.

- [ ] **Step 1: Write the failing tests:** on a 3-case inline set, `summarize(results)` gives the right counts per bucket; the runner's exit code is 1 when a crafted false accept exists.
- [ ] **Step 2:** Run `uv run pytest tests/eval -v`. Expected: FAIL.
- [ ] **Step 3:** Implement the converter, the generator and the runner. Write the hand-written cases.
- [ ] **Step 4:** Run `uv run python eval/generate_cases.py && uv run python eval/run_verifier_eval.py --fail-on-false-accept`.
  - **Expected:** ≥ 300 total cases; FA = 0; FR ≤ 2%; inconclusive ≤ 5%; p95 < 1 s.
  - **If a threshold is missed, stop and report the failing cases.** Fix the verifier; do not relabel.
- [ ] **Step 5: Commit** `eval: verifier evaluation set, runner, CI gate`. Include `eval/report.md`.

---

### Task 11: Domain types and mastery

**Files:**
- Create: `src/mathtutor/domain.py`, `src/mathtutor/mastery/__init__.py`, `scores.py`, `tests/mastery/test_scores.py`

**Interfaces:**
- Produces, in `domain.py`:

```python
Mode = Literal["diagnostic", "practice", "recap"]
ExamConditions = Literal["closed_book", "formula_sheet", "open_notes"]
ItemKind = Literal["problem", "recall", "concept"]
Band = Literal["not_seen", "weak", "shaky", "strong"]

@dataclass(frozen=True)
class SessionPlan:
    mode: Mode; topics: tuple[str, ...]; minutes_budget: int
    exam_conditions: ExamConditions; warmup_enabled: bool

@dataclass(frozen=True)
class AttemptRecord:
    item_id: str; item_kind: ItemKind; topic: str
    status: Status; is_first_attempt: bool; is_multiple_choice: bool
    revealed: bool; session_id: int; created_at: datetime
```

- Produces, in `mastery/scores.py`:
  - `@dataclass(frozen=True) class TopicMastery: recall: float; recall_band: Band; application: float; application_band: Band; application_n: int`
  - `def compute_mastery(attempts: Sequence[AttemptRecord], topics: Iterable[str]) -> dict[str, TopicMastery]`
  - `def band(score: float, n_counted: int) -> Band`

  Implements §6.1 exactly. A `not_seen` topic reports score 0.5.

- [ ] **Step 1: Write the failing tests** (hand-computed values):

```python
def test_empty_is_not_seen(): m = compute_mastery([], ["t"])["t"]; assert (m.application, m.application_band) == (0.5, "not_seen")
def test_two_correct(): ...           # two first-attempt correct: weights 1 (newest, k=0) and 0.5**0.1 ≈ 0.9330; score = 2.9330/3.9330 ≈ 0.7457 → "shaky"
def test_only_first_attempts_count(): ...
def test_mc_half_weight(): ...
def test_unable_excluded(): ...
def test_recall_and_application_separate(): ...
def test_band_edges(): assert band(0.5, 2) == "shaky" and band(0.8, 2) == "strong" and band(0.49, 2) == "weak" and band(0.9, 1) == "not_seen"
```

- [ ] **Step 2:** Run `uv run pytest tests/mastery -v`. Expected: FAIL.
- [ ] **Step 3:** Implement. Here k is the number of newer counted attempts for that user, in that topic and that score.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(mastery): recall and application scores`.

---

### Task 12: Persistence (SQLAlchemy + Alembic)

**Files:**
- Create: `src/mathtutor/store/__init__.py`, `models.py`, `db.py`, `repo.py`, `alembic.ini`, `migrations/env.py`, `migrations/versions/0001_initial.py`, `tests/store/test_repo.py`, `tests/store/test_migrations.py`

**Interfaces:**
- Produces:
  - ORM classes `User`, `StudySession`, `Attempt` with exactly the §5 columns. `topics` is a JSON column; times are timezone-aware UTC.
  - `make_engine(url: str) -> Engine` (SQLite: `PRAGMA foreign_keys=ON`, WAL)
  - `make_sessionmaker(engine) -> sessionmaker[Session]`
  - in `repo.py`, all taking `db: Session`:
    - `create_user(db, username, password_hash) -> User`, raising `UsernameTaken`
    - `get_user_by_username(db, username) -> User | None`
    - `create_study_session(db, user_id: int, plan: SessionPlan, now: datetime) -> StudySession`
    - `get_study_session(db, session_id) -> StudySession | None`
    - `set_current_item(db, s: StudySession, item_id: str | None, now: datetime) -> None`
    - `record_attempt(db, **fields) -> Attempt`
    - `attempts_for_user(db, user_id) -> list[Attempt]` (by created_at)
    - `attempts_for_session(db, session_id) -> list[Attempt]`
    - `end_session(db, s, now) -> None`
    - `set_warmup(db, s, enabled: bool) -> None`
  - Consumes `SessionPlan` from `mathtutor.domain` (Task 11).

- [ ] **Step 1: Write the failing tests:**
  - create/get user
  - a duplicate username raises `UsernameTaken`
  - session round-trips the topics list
  - attempts are ordered
  - foreign keys are enforced
  - `test_migrations`: `alembic upgrade head` on an empty temp DB produces the same tables and columns as `Base.metadata`
- [ ] **Step 2:** Run `uv run pytest tests/store -v`. Expected: FAIL.
- [ ] **Step 3:** Implement. Generate `0001_initial` with autogenerate, then hand-check it.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(store): models, repository, initial migration`.

---

### Task 13: Policy framework, diagnostic, recap, baseline

**Files:**
- Create: `src/mathtutor/recommend/__init__.py`, `base.py`, `budget.py`, `diagnostic.py`, `recap.py`, `baseline.py`, `tests/recommend/conftest.py` (a small in-memory `ContentBank` builder), `tests/recommend/test_diagnostic.py`, `test_recap.py`, `test_baseline.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class Selection: item_id: str | None; reason: str

@dataclass(frozen=True)
class PolicyContext:
    bank: ContentBank; plan: SessionPlan
    user_attempts: Sequence[AttemptRecord]        # all of this user's, incl. this session
    session_attempts: Sequence[AttemptRecord]
    mastery: Mapping[str, TopicMastery]
    session_started_at: datetime; now: datetime
    rng: random.Random                             # web seeds with the session id on every call

class Policy(Protocol):
    def select(self, ctx: PolicyContext) -> Selection: ...

def estimated_minutes(bank: ContentBank, item_id: str) -> float      # §6.2
def eligible_recall_items(bank: ContentBank, topics: Sequence[str], exam: ExamConditions) -> list[FormulaItem]  # §6.3
def policy_for(mode: Mode) -> Policy
```

- **Diagnostic (§6.4):**
  - Build a deterministic item list from `ctx.rng` and the attempts made **before** `session_started_at`, so "unseen" does not change mid-session.
  - Fit the list to the budget, then fall back to 1 problem per topic, then truncate topics in textbook order.
  - Return the first item not yet attempted in the session, or `Selection(None, "diagnostic complete")`.
- **Recap:** eligible recall and concept items for the topics, in topic order, each once. Then `None` with "recap complete".
- **Baseline:** topics by `order`, problems by difficulty ascending, skipping items already attempted in the session.

- [ ] **Step 1: Write the failing tests:**
  - diagnostic with 2 topics and a 60-minute budget → per topic, 1 recall item then 2 problems at difficulty 2–3, in topic order
  - with a 5-minute budget → 1 problem per topic
  - the same seed gives the same list
  - items already attempted in the session are skipped
  - `open_notes` → only concept items appear
  - recap with `formula_sheet` → only `core` recall items plus concept items
  - baseline order
  - every `Selection.reason` is non-empty
- [ ] **Step 2:** Run `uv run pytest tests/recommend -v`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(recommend): diagnostic, recap, baseline policies`.

---

### Task 14: Practice policy

**Files:**
- Create: `src/mathtutor/recommend/practice.py`, `tests/recommend/test_practice.py`
- Modify: `policy_for` (wire `practice`)

**Interfaces:**
- Produces: `class PracticePolicy(Policy)`, plus `def current_level(attempts: Sequence[AttemptRecord], bank: ContentBank, topic: str) -> int`. The level replays the user's first-attempt problem history in that topic: start at 2, +1 after 2 consecutive correct, −1 on incorrect, clamped to 1–5.
- **Order of checks:**
  1. **Time:** if `now − session_started_at ≥ minutes_budget` → `None`, reason "time budget reached".
  2. **Warm-up:** if `plan.warmup_enabled`, fewer than 6 recall or concept attempts in the session, and an eligible item not yet attempted in the session exists → choose the one with the lowest recall score (ties broken by id). Reason "Warm-up: …".
  3. **Topic:** the selected topic with the lowest application score. If a prerequisite (in the full graph) is `weak` and has servable problems, use the prerequisite instead. Reason "Prerequisite check: <topic> is weak".
  4. **Problem, with fallbacks (Review Focus 3):**
     1. unseen problems at `current_level`
     2. unseen at the nearest level (ties go lower)
     3. seen problems whose latest attempt was incorrect, oldest first
     4. repeat for the next-weakest selected topic
     5. `None`, reason "no more problems available for the selected topics"

- [ ] **Step 1: Write the failing tests:**

```python
def test_warmup_first_then_problems(): ...
def test_warmup_capped_at_6(): ...
def test_warmup_disabled_skips(): ...
def test_weakest_topic_chosen(): ...
def test_prerequisite_check_reason(): ...         # reason starts with "Prerequisite check:"
def test_level_up_after_two_correct(): assert current_level([...c, c], bank, "t") == 3
def test_level_down_and_clamp(): ...
def test_nearest_difficulty_fallback(): ...       # only difficulty-5 problems exist, level 2 → picks the 5
def test_seen_incorrect_fallback(): ...
def test_exhausted_returns_none_with_reason(): ... # Review Focus 3 — never raises
def test_time_budget_reached(): ...               # Review Focus 4 — now = start + budget → None
```

- [ ] **Step 2:** Run `uv run pytest tests/recommend/test_practice.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `uv run pytest tests/recommend -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(recommend): adaptive practice policy with warm-up`.

---

### Task 15: Web foundation — settings, app, auth, security, errors, logging

**Files:**
- Create: `src/mathtutor/web/__init__.py`, `settings.py`, `app.py`, `auth.py`, `security.py`, `errors.py`, `logging.py`, `tests/web/conftest.py`, `tests/web/test_auth.py`, `tests/web/test_security.py`

**Interfaces:**
- Produces:
  - `class Settings(BaseSettings)` with:
    - `secret_key: str`
    - `database_url: str = "sqlite:///./data/mathtutor.db"`
    - `content_dir: Path = Path("content")`
    - `secure_cookies: bool = True`
    - `verifier_timeout_s: float = 3.0`
    - `verifier_workers: int = 2`
  - `def create_app(settings: Settings) -> FastAPI`. Startup does `load_content`, engine and sessionmaker, `VerifierPool`; these are stored on `app.state`. Shutdown closes the pool.
  - **Auth:** Starlette `SessionMiddleware` with a signed cookie, `https_only=settings.secure_cookies`, `same_site="lax"`.
    - `hash_password`, `verify_password` (argon2)
    - dependency `current_user(request, db) -> User`, which raises a 401 `ApiError`
    - routes `POST /api/auth/register|login|logout`, enforcing the username and password rules from Global Constraints
  - **CSRF:** the token lives in the session; every non-GET request must send header `X-CSRF-Token` or form field `csrf_token`. `GET /api/auth/csrf` returns it.
  - **Rate limiting:** `class RateLimiter(limit: int, window_s: float)`, an in-memory sliding window with `hit(key) -> bool`. Exceeding it raises a 429 `ApiError`.
  - **Errors:** `class ApiError(Exception): status: int; code: str; message: str`. Handlers render `{error, message}`; pydantic validation errors become 422 with `error="validation"`.
  - **Logging:** structlog JSON with a `request_id` middleware.
  - `GET /healthz` returns `{status: "ok"}`.

- [ ] **Step 1: Write the failing tests:**
  - register → login → logout works
  - a bad username or short password → 422
  - a duplicate username → 409 `username_taken`
  - a wrong password → 401
  - a POST without a CSRF token → 403
  - the 11th login within a minute → 429
  - `/healthz` → 200
  - the password does not appear in captured logs
- [ ] **Step 2:** Run `uv run pytest tests/web -v`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(web): app factory, auth, CSRF, rate limits, errors, logging`.

---

### Task 16: Session and attempt API

**Files:**
- Create: `src/mathtutor/web/flow.py` (the glue: building `PolicyContext`, deciding when an item is finished, converting rows to `AttemptRecord`), `src/mathtutor/web/api.py`, `tests/web/test_session_api.py`

**Interfaces:**
- Consumes: Tasks 7, 8, 11–15.
- Produces the §7.2 endpoints, plus `POST /api/sessions/{id}/skip-warmup`, which sets `warmup_enabled=False`.
- In `flow.py`:
  - `def item_finished(mode: Mode, attempts_on_item: Sequence[Attempt]) -> bool`
    - diagnostic: after 1 attempt
    - otherwise: after a correct attempt, a revealed attempt, or 3 attempts
  - `def next_selection(db, bank, session, now) -> Selection`
    - Seeds `random.Random(session.id)` and builds `PolicyContext`.
    - On `None`, it ends the session.
    - Otherwise it sets the current item.
- **`POST /api/attempts` flow:**
  1. Check ownership → 403.
  2. If the session has ended, or the item is not current, or the item is already finished → 409 `not_current` (Review Focus 5).
  3. Call `pool.check`.
  4. A `FormatIssue` → 200 `{format_issue: {code, message}}`; no attempt is recorded.
  5. Otherwise record the attempt with `seconds_spent = now − current_item_served_at`. Fill in `is_first_attempt` and `attempt_number`, and use `bank.item_version`.
  6. In diagnostic mode, the response leaves out the verdict: `{recorded: true}`.
  7. In other modes it returns `{verdict, can_retry, can_reveal}`.
- **`next`:** if the current item is not finished, return it again, so a page refresh is safe. Once time is up, the in-progress item is still graded (Review Focus 4).
- **Responses never include the expected answer,** except from `/reveal`.
- **`/reveal`:** practice only, problems only, after 3 tries. It records `revealed=True` on the last attempt and returns `{answer_latex}`, where `answer_latex = sympy.latex(parse_expected(spec))`.

- [ ] **Step 1: Write the failing tests:**
  - **Full flows** via `TestClient`, with a temp DB, the seed content and `verifier_workers=1`:
    - diagnostic → report (bands per topic)
    - practice with warm-up → skip-warmup → wrong ×3 → reveal → next
    - recap
  - another user's session → 403
  - submitting a non-current item → 409
  - **Review Focus 5:** a double submit after a correct answer → 409, and the attempt count is unchanged
  - **Review Focus 4:** with the time budget expired mid-item (inject a clock via `app.state.clock`), the submit is graded and `next` returns `{done: true}`
  - **Format issues:** a format issue records no attempt
  - **No answer leaks:** none of the `/next` payloads contain the expected answer string
- [ ] **Step 2:** Run `uv run pytest tests/web/test_session_api.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement. The clock is `app.state.clock: Callable[[], datetime]`, defaulting to UTC now.
- [ ] **Step 4:** Run `uv run pytest -v`. Expected: the whole suite passes.
- [ ] **Step 5: Commit** `feat(web): session, attempt, reveal, report, mastery API`.

---

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

### Task 19: Containerization and backups

**Files:**
- Create: `deploy/Dockerfile`, `deploy/docker-compose.yml`, `deploy/Caddyfile`, `deploy/backup.sh`, `deploy/entrypoint.sh`, `.dockerignore`, `tests/test_deploy_files.py`

**Interfaces:**
- **Image:** `python:3.12-slim`, a non-root user, `uv sync --frozen --no-dev`. `entrypoint.sh` runs `alembic upgrade head` and then `uvicorn mathtutor.web.app:app --host 0.0.0.0 --port 8000`. A `HEALTHCHECK` hits `/healthz`.
- **Compose:** services `app` (volume `./data:/app/data`, `env_file: .env`) and `caddy` (ports 80/443, `Caddyfile` with `{$DOMAIN} { reverse_proxy app:8000 }`).
- **`backup.sh`:** `sqlite3 data/mathtutor.db ".backup /tmp/…"` → `aws s3 cp` to `s3://$BACKUP_BUCKET/mathtutor-<UTC date>.db`, then deletes all but the newest 14. It is run nightly by host cron (documented in the README).

- [ ] **Step 1: Write the failing test** (static checks): the Dockerfile has a non-root `USER` and a `HEALTHCHECK`; the compose file defines no secrets inline; `backup.sh` keeps exactly 14.
- [ ] **Step 2:** Run `uv run pytest tests/test_deploy_files.py -v`. Expected: FAIL, then implement.
- [ ] **Step 3:** Run `docker build -f deploy/Dockerfile -t mathtutor .`, then `docker run` with a temp `.env`, then `curl localhost:8000/healthz`. Expected: `{"status":"ok"}`.
- [ ] **Step 4: Commit** `build: Docker image, compose with Caddy, S3 backup script`.

---

### Task 20: Deploy, budget guard, README

Manual AWS steps are listed for you, the developer, to perform. Claude does not create cloud resources.

**Files:**
- Create: `.github/workflows/deploy.yml`, `docs/deploy.md`
- Modify: `README.md`

**Interfaces:**
- **`deploy.yml`:**
  - on push to `main` after CI passes, build and push `ghcr.io/<owner>/mathtutor:<sha>` and `:latest`
  - SSH to the host (secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`)
  - run `docker compose pull && docker compose up -d`
  - then `curl -fsS https://$DOMAIN/healthz`
- **`docs/deploy.md`, a checklist for you:**
  - Lightsail $5 instance with Docker installed and a static IP
  - domain A record pointing at it
  - S3 bucket plus an IAM user restricted to that bucket
  - `.env` on the host
  - the crontab line for `backup.sh`
  - an AWS Budget of $10/month with an email alert
- **README:**
  - what it is
  - an architecture diagram (Mermaid)
  - how to run locally (`uv sync`, `.env.example`, `uv run uvicorn …`)
  - how to run the tests and the evaluation
  - the latest `eval/report.md` table
  - limitations (from §1.3 and the risks)
  - roadmap to sub-projects 2–4

- [ ] **Step 1:** Add the `tests/test_readme.py` check: the README contains the section headings "Architecture", "Run locally", "Verifier evaluation" and "Limitations", and `.env.example` lists `SECRET_KEY` and `DATABASE_URL`. Run it: FAIL, then write the docs, then PASS.
- [ ] **Step 2:** You do the `docs/deploy.md` checklist. Then push to `main`.
- [ ] **Step 3: Verify (§11).**
  - `https://<domain>/healthz` returns ok.
  - Both CI and deploy workflows pass.
  - One manual diagnostic, practice and recap run on the live site succeeds.
  - Record the results in the README.
- [ ] **Step 4: Commit** `docs: deployment workflow, README, deploy checklist`.
