[Index](../2026-10-13-core-practice-loop.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 17–53. Review findings remain unresolved.

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
- Commit attribution: no assistant coauthor trailers; acknowledge Claude and Codex in README.

<!-- End preserved source. -->
