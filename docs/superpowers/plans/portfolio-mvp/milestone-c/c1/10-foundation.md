# C1 tasks 1–2: configuration and the LaTeX parser

[C1 plan](README.md) · [Interfaces](03-interfaces.md) · Next: [guard](11-guard.md)

### Task 1: Help settings and versioned config

**Files:** Create `src/mathtutor/help/__init__.py`, `help/config.py`, `help/help_config.json`,
`help/messages.py`; Modify `src/mathtutor/settings.py`; Test `tests/unit/help/test_config.py`.

**Interfaces:** Produces `HelpConfig`, `load_help_config`, `worst_case_micros` (03); settings
`anthropic_api_key: SecretStr | None = None`, `corpus_path: Path = Path("content/corpus/chunks.jsonl")`,
`help_generator: Literal["claude", "scripted", "off"] = "claude"`, `guard_pool_memory_mb: int = 384`.

- [ ] **Step 1: Failing tests**
  - `test_config_values`: loading the committed JSON gives `model == "claude-haiku-5-5"`,
    `deadline_s == 15.0`, `max_calls == 2`, `admission.month_budget_micros == 15_000_000`, and every
    value in [pinned values](01-pinned-values.md).
  - `test_worst_case_haiku`: `worst_case_micros(cfg, "claude-haiku-5-5") == 1_300`.
  - `test_unknown_key_rejected`: an extra JSON key raises `ValueError`.
  - `test_scripted_only_in_test_env`: `Settings(env="production", help_generator="scripted", ...)` raises.
  - `test_messages_us_spelling`: messages contain no `licence|colour|behaviour`; exact copy of
    `UNAVAILABLE = "Hints are unavailable right now."`, `LIMITED = "You've reached the help limit for now."`,
    `ABSTAIN = "I can't answer that from the textbook."`, `NUDGE = "Here's a nudge without the answer: re-read {section}."`.
- [ ] **Step 2:** `uv run pytest tests/unit/help/test_config.py -q` → FAIL (module missing).
- [ ] **Step 3:** Implement with pydantic models (`extra="forbid"`, frozen) mirroring 03; JSON holds
  every value from 01. Package the JSON with the wheel (hatch includes package data under `src/`).
- [ ] **Step 4:** Same command → PASS; `uv run mypy src` clean.
- [ ] **Step 5:** Commit `feat(help): versioned help config and settings`.

### Task 2: Allowlisted LaTeX → MathJSON parser

**Files:** Create `src/mathtutor/help/latex_parse.py`; Test `tests/unit/help/test_latex_parse.py`.

**Interfaces:** Produces `parse_latex`, `ParsedMath`, `ParseRejected` (03). Output trees use the
MathJSON heads `verify/translate.py` accepts (`Add`, `Subtract`, `Negate`, `Multiply`, `Divide`,
`Power`, `Sqrt`, `Root`, `Sin`…`Csc`, `Ln`, `Log`, `Exp`, `Abs`, `Rational`, numbers, symbols).

- [ ] **Step 1: Failing tests**
  - `test_bank_answers_roundtrip` (marks the test as using SymPy; lives under `tests/unit/help`
    but imports `mathtutor.verify.check` directly, which is allowed in tests): for each of the 22
    compiled problems with an expression/numeric answer and each choice's LaTeX,
    `check(CheckRequest(spec, SubmittedAnswer(kind, parse_latex(latex).tree, latex, None)))` is `correct`.
  - `test_notation_table`: parametrized; each must parse with `foreign == frozenset()`:
    `2x\cos x - x^2\sin x`, `x(2\cos x - x\sin x)`, `\left(3x^2+1\right)^{2}`, `6x\cdot(x^2+1)^2`,
    `\dfrac{1}{x}`, `\tfrac12 x^{-1/2}`, `\sqrt[3]{x}`, `\sin^2 x`, `\sec x\tan x`, `e^{2x}`, `\ln|x|`, `-\frac{200}{49}`, `0.54`.
  - `test_foreign_symbols`: `3u^2` → foreign `{"u"}`; `f'(x)` → `{"f'"}`; `\frac{d}{dx}(x^2)` → `{"d/dx"}`;
    `g(x)h'(x)` → `{"g", "h'"}`. The tree still parses.
  - `test_rejects`: `\begin{matrix}`, `\int x\,dx`, `\lim_{x\to0}`, unbalanced braces, `x^{` ,
    401-byte input, depth 25 nesting, 201 nodes → `ParseRejected` with a reason.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement a recursive-descent tokenizer/parser over an explicit command allowlist;
  implicit multiplication by juxtaposition; `\left`/`\right`/`\,`/`\!` dropped; `\sin^n x` →
  `Power(Sin(x), n)`; function argument without braces binds the next factor (`\sin 7x` → `Sin(7x)`,
  matching `latex_rules.py`'s reading). Single letters other than `variable`, `e`, `\pi` are foreign.
  No `eval`, `sympify` or `parse_expr`. Record `PARSER_VERSION = "1"` in `help_config.json`.
- [ ] **Step 4:** Run → PASS. Add a Hypothesis fuzz test `test_never_raises` (random printable
  strings ≤ 400 bytes return either type, never raise) and run it.
- [ ] **Step 5:** Commit `feat(help): allowlisted LaTeX parser for the leak guard`.
