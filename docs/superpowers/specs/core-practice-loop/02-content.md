[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 80–159. Review findings remain unresolved.

## 3. Content model

### 3.1 Topics (`content/topics.yaml`)

Fields: `id`, `name`, `area`, `order` (textbook order), `openstax_sections`, `prerequisites`.

| order | id | area | OpenStax § | prerequisites |
|---|---|---|---|---|
| 1 | `limits.intuitive` | Limits | 2.2 | — |
| 2 | `limits.laws` | Limits | 2.3 | limits.intuitive |
| 3 | `continuity` | Continuity | 2.4 | limits.laws |
| 4 | `theorems.ivt` | Theorems | 2.4 | continuity |
| 5 | `derivatives.definition` | Derivatives | 3.1–3.2 | limits.laws |
| 6 | `derivatives.basic_rules` | Derivatives | 3.3 | derivatives.definition |
| 7 | `derivatives.trig` | Derivatives | 3.5 | derivatives.basic_rules |
| 8 | `derivatives.chain_rule` | Derivatives | 3.6 | derivatives.basic_rules, derivatives.trig |
| 9 | `derivatives.implicit` | Derivatives | 3.8 | derivatives.chain_rule |
| 10 | `derivatives.exp_log` | Derivatives | 3.9 | derivatives.chain_rule |
| 11 | `theorems.mvt` | Theorems | 4.4 | continuity, derivatives.basic_rules |
| 12 | `limits.infinity` | Limits | 2.2, 4.6 | limits.laws |
| 13 | `integrals.antiderivatives` | Integrals | 4.10 | derivatives.basic_rules, derivatives.trig, derivatives.exp_log |
| 14 | `integrals.ftc` | Integrals | 5.3 | integrals.antiderivatives |
| 15 | `integrals.substitution` | Integrals | 5.5 | integrals.ftc, derivatives.chain_rule |

The prerequisite graph must be acyclic. This is enforced at load time.

### 3.2 Problems (`content/problems/*.yaml`)

```yaml
id: openstax-c1-3.6-221            # unique, stable
topic: derivatives.chain_rule
difficulty: 2                       # 1–5, rubric §4.3
source: {book: "OpenStax Calculus Volume 1", section: "3.6", exercise: 221,
         url: "https://openstax.org/books/calculus-volume-1/pages/3-6-the-chain-rule",
         license: "CC BY-NC-SA 4.0"}
statement: "Find $\\frac{dy}{dx}$ for $y = \\sin(3x^2)$."   # Markdown + $LaTeX$
answer_type: expression
answer: "6*x*cos(3*x**2)"           # SymPy syntax; trusted content
variable: x
sample_domain: [-5, 5]              # where numeric spot-checks are valid
decimals: 3                         # numeric/limit/point_set only; null = exact only
choices: null                       # multiple_choice only: list of {id, text}
relation: null                      # implicit_derivative only, e.g. "x**2 + y**2 - 25"
status: human_verified              # human_verified | auto_verified | computed_only | needs_review
```

- `answer_type` is one of `numeric`, `expression`, `antiderivative`, `limit`, `implicit_derivative`, `point_set`, `multiple_choice`.
  - Under `antiderivative`, `answer` is **one** antiderivative (not the integrand).
  - `limit` answers may be `oo`, `-oo`, or `DNE`.
  - `point_set` answers are a YAML list.
- `decimals` defaults to 3 when absent, for the types where it applies.
- Only `human_verified`, `auto_verified` and `computed_only` problems are served. Sub-project 1 ships only `human_verified` problems; the other statuses exist for sub-project 2.
- **Content version:** `problem_version` = the first 12 hex characters of the SHA-256 of the problem's canonical JSON. Each attempt stores it.

### 3.3 Formula and concept items (`content/formulas/*.yaml`)

```yaml
- id: deriv.product_rule
  topic: derivatives.basic_rules
  kind: recall                      # recall | concept
  prompt: "Product rule: $\\frac{d}{dx}[f(x)g(x)] = $ ?"
  answer_type: expression           # recall → expression; concept → multiple_choice
  answer: "fp*g + f*gp"
  functions: [f, g]                 # abstract functions allowed in the student answer
  memorize: core                    # recall only: core (always memorized) | sheet (commonly provided)
```

- **Recall** items: about 5–10 per topic.
- **Concept** items: about 2 per topic, `multiple_choice`, written by the developer.
- Commonly used professor cheat sheets inform *which* formulas exist and whether each is `core` or `sheet`. The wording is our own; sheets are not copied.
- The per-topic **formula sheet** is rendered from the same recall entries.
- Abstract functions: in the student's MathJSON, `f(x)` maps to symbol `f` and `f'(x)` maps to symbol `fp` (likewise `g`/`gp`). This is allowed only for names listed in `functions`.

### 3.4 Seed content for sub-project 1

- 20 `human_verified` problems covering all 15 topics, with every `answer_type` used at least once.
- Recall and concept items for all 15 topics.

---

<!-- End preserved source. -->
