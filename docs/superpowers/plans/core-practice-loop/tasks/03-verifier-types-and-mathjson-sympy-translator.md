[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 184–271. Review findings remain unresolved.

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

<!-- End preserved source. -->
