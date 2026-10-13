[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 182–220. Review findings remain unresolved.

### 4.2 Equivalence and per-type rules

Equivalence for expression-like comparisons:
1. **Symbolic:** `simplify(student - expected) == 0` → `correct`, method `symbolic`.
2. **Numeric:**
   - Draw 20 points uniformly from `sample_domain` (seeded) and evaluate both expressions with mpmath at 50 digits.
   - Skip a point only if the **expected** value is non-finite or non-real there.
   - If the expected value is defined but the student's is not → `incorrect`, reason `student_undefined`.
   - If any valid point has |s − e| > 1e-8 · max(1, |e|) → `incorrect`, method `numeric`.
   - If all valid points agree and there are ≥ 10 of them → `correct`, method `numeric`.
   - Otherwise → `unable_to_verify`, reason `insufficient_sample_points`.

| answer_type | Rule |
|---|---|
| `expression` | Equivalence as above |
| `antiderivative` | Equivalence of d/dx(student) against d/dx(expected) |
| `numeric` | An exact student input is checked symbolically, then numerically at 50 digits. A decimal input with ≥ `decimals` places is `correct` iff round(expected, decimals) == round(student, decimals). |
| `limit` | `oo` / `-oo` / `DNE` must match exactly; otherwise as `numeric` |
| `point_set` | The two sets must have the same size and admit a one-to-one numeric match (as `numeric`), in any order |
| `implicit_derivative` | Pick 20 x-values in `sample_domain`, solve `relation` for real y numerically (`nsolve` from several starts), and compare at (x, y) pairs with the numeric rule. With < 10 valid pairs → `unable_to_verify`. |
| `multiple_choice` | Choice id equality |

**Input-format pre-checks.** These return a format message and **do not create an attempt**:
- empty input
- a decimal with fewer than `decimals` places
- a decimal when `decimals` is `null`

The UI always shows the precision rule under the input: "Enter an exact value, or a decimal rounded to N places" / "Exact answer required".

### 4.3 Difficulty rubric (author-assigned)

| Level | Description |
|---|---|
| 1 | One rule, applied directly |
| 2 | One rule plus light algebra |
| 3 | Two rules combined, or a domain/sign subtlety |
| 4 | Three or more steps, or a nontrivial setup |
| 5 | Multi-concept, or an exam-style trap |

<!-- End preserved source. -->
