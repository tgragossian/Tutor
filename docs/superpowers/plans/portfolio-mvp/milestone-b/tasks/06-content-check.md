# Task 6: Content math check and statement HTML

[Milestone B plan](../README.md) · [Spec 01](../../../../specs/2026-10-13-portfolio-core/01-content-and-domains.md) · Rulings R1, R3

**Files:**
- Create: `src/mathtutor/verify/content_check.py`, `tests/unit/verify/test_content_check.py`
- Create fixtures: `tests/fixtures/content/bundles/{expected_pole,expected_untranslatable,choice_bad}.json`
- Modify:
  - `tools/compile_content/compile.mjs`, `compile.test.mjs`, `tools/package.json` (+ `markdown-it`, exact pin)
  - `src/mathtutor/content/schema.py` (`schema_version: Literal[2]`, `Problem.statement_html: str`)
  - `content/compiled/problems.json` (regenerated), `Dockerfile`, `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `load_bundle` (task 1), `translate`, `equivalent`, `check` (tasks 3–5).
- Produces:
  - `def check_bundle(content: LoadedContent) -> list[str]` — one error line per problem, in the loader's `<id>: <field>: <reason>` format.
  - CLI: `python -m mathtutor.verify.content_check [path]` → exit 0 and `ok: N problems`, or exit 1 and the error lines.
  - Compiled problems gain `statement_html` (consumed by task 13's `PublicItem`).

- [ ] **Step 1: Write the failing tests.**

```python
def test_seed_bundle_passes(): assert check_bundle(load_bundle(REAL)) == []
def test_expected_answer_must_translate(): assert "answer.latex: does not translate" in check_bundle(load(EXPECTED_UNTRANSLATABLE))[0]
def test_expected_answer_undefined_on_domain(): assert "answer.domain" in check_bundle(load(EXPECTED_POLE))[0]   # 1/x on ℝ (spec 04 row 7)
def test_choices_each_translate_and_correct_differs(): ...  # choice_bad: two choices provably equal → error
def test_misconceptions_are_not_correct(): ...   # a misconception string graded against the expected answer must not be correct
```

```js
test("statement_html renders inline math as read-only math-field", ...)  // "$x^2$" → <math-field read-only>x^2</math-field>
test("statement raw HTML is escaped", ...)                                 // "<script>" → &lt;script&gt;
test("statement links outside openstax.org are dropped", ...)
```

- [ ] **Step 2:** Run `uv run pytest tests/unit/verify/test_content_check.py -q` and `npm test --prefix tools`. Expected: FAIL.
- [ ] **Step 3: Implement `check_bundle`.** For every problem:
  - expression/numeric: the expected tree translates; it is proven equal to itself; each of its constraints has an empty violation set inside the declared domain (else `answer.domain: expected answer undefined on domain at <set>`; a `ConditionSet` → `domain unprovable`).
  - choice: every choice translates; the `correct` choice is not proven equal to any other choice.
  - misconceptions (the part before `  #`): if parseable as LaTeX they were compiled to MathJSON by task 6's compiler change; each must not grade `correct`.
- [ ] **Step 4: Compiler.**
  - `statement_html`: split the statement on `$...$`; render text parts with `markdown-it({html: false, linkify: false})` inline rendering; drop any link whose href does not start with `https://openstax.org/`; render math parts as `<math-field read-only>` + HTML-escaped LaTeX + `</math-field>`.
  - Misconceptions: compile the LaTeX part to `misconceptions_mathjson` (list, same order). Add that optional field to `Problem` too.
  - Bump `schema_version` to 2 in compiler output and schema.
- [ ] **Step 5: Wire it in.**
  - CI `python` job: `uv run python -m mathtutor.verify.content_check` after pytest.
  - `Dockerfile` build stage: `RUN /app/.venv/bin/python -m mathtutor.verify.content_check /src/content/compiled/problems.json` (copy `content/compiled` into the build stage first). The image cannot be built from a bad bundle.
- [ ] **Step 6:** Run `npm run compile --prefix tools && uv run pytest -q && npm test --prefix tools`. Expected: PASS, and `git diff content/compiled` shows only `statement_html`, `misconceptions_mathjson` and `schema_version`.
- [ ] **Step 7: Commit** `feat: offline content math check; statement HTML at compile time`.
