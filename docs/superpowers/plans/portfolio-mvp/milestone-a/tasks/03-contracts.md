# Task 3: Domain enums, content schema, API contracts

[Milestone A plan](../README.md) · [Spec 01](../../../../specs/2026-10-13-portfolio-core/01-content-and-domains.md) · [Spec 02](../../../../specs/2026-10-13-portfolio-core/02-answer-contracts.md) · [Spec 07](../../../../specs/2026-10-13-portfolio-core/07-application-and-web.md#dtos)

**Files:**
- Create:
  - `src/mathtutor/domain.py`
  - `src/mathtutor/content/__init__.py`, `src/mathtutor/content/schema.py`
  - `src/mathtutor/web/__init__.py`, `src/mathtutor/web/schemas.py`
  - `contracts/README.md`
  - `contracts/examples/submit-expression.json`, `submit-numeric.json`, `submit-choice.json`, `item-expression.json`, `item-choice.json`
- Test:
  - `tests/unit/test_content_schema.py`
  - `tests/unit/test_api_contracts.py`

**Interfaces:**
- Consumes: the MathJSON shapes from ADR 0002 (typed as `JsonValue` and never interpreted here).
- Produces:
  - **`domain.py`**, all `StrEnum`:
    - `AnswerKind{EXPRESSION, NUMERIC, CHOICE}`
    - `ReviewStatus{HUMAN_VERIFIED, NEEDS_REVIEW}`
    - `ItemState{ACTIVE, ANSWERED, EXHAUSTED, REVEALED, COMPLETED}`
    - `Action{SUBMIT, ADVANCE, SKIP, REVEAL}`
    - `VerdictStatus{CORRECT, INCORRECT, UNABLE_TO_VERIFY}`
    - `FormatIssueCode{EMPTY, INCOMPLETE, EXACT_REQUIRED, INPUT_TOO_LARGE, UNSUPPORTED_NOTATION}`
    - the constant `MAX_TRIES = 3`
  - **`content/schema.py`:**
    - `Source`, `Interval`, `Domain`, `Precision`, `Choice`, `Review`
    - `ExpressionAnswer | NumericAnswer | ChoiceAnswer`, discriminated by `kind`
    - `Topic(topic_id, title, order: int, section)`, `Problem` (`problem.topic` is a `topic_id`)
    - `ContentBundle(schema_version: Literal[1], tools: ToolVersions, topics: list[Topic], problems: list[Problem])`
  - **`web/schemas.py`:**
    - `SubmissionRequest`, with the answer models `ExpressionAnswerIn | NumericAnswerIn | ChoiceAnswerIn` discriminated by `kind`
    - `PublicChoice(id, label_latex)`
    - `PublicItem`
    - `ErrorBody(error: str, message: str)`

**Field rules (beyond spec 01's YAML example):**
- **`Source`:**
  - `book`, `section`, `exercise: int | None`
  - `url` must start with `https://openstax.org/`
  - `license: Literal["CC BY-NC-SA 4.0"]`
  - `adapted: bool = False` (true for author-written variants, such as the choice items)
- **`Interval`:** a 4-tuple `[lo, hi, lo_kind, hi_kind]`. Bounds are `-inf`, `inf` or a rational string (`^-?\d+(/\d+)?$`); `lo < hi` by `fractions.Fraction`; infinite ends are `open`.
- **`Domain`:** at least one interval; each `exclude` entry is a rational inside some interval.
- **`Precision`:** `{"decimals": 0..10}` or the literal `"exact"`. Only valid on `numeric`, where it's required.
- **Compiled answers** carry `latex` plus `mathjson: JsonValue`.
  - `ChoiceAnswer` has `choices` (2–6, with unique ids each `{id, latex, mathjson}`) and `correct`, which must be one of those ids.
  - `ExpressionAnswer` and `NumericAnswer` have `variable` (default `x`), `domain` and `strict_domain`.
- **`Problem`:**
  - `id`, `topic`, `difficulty` (1–5), `source`, `statement`, `answer`, `misconceptions: list[str] = []`, `review`
  - `review.reviewer` must not be empty when the status is `human_verified`.

**API rules:**
- `submission_id` must be a UUID version 4.
- `session_item_id` > 0; `item_revision` ≥ 0.
- `latex` is at most 2000 characters.
- `choice_id` matches `^[a-z]$`.
- `PublicItem`:
  - `session_item_id`, `revision`, `statement_html`, `answer_kind`, `precision_hint: str | None`, `choices: list[PublicChoice] | None`, `source`, `allowed_actions: list[Action]`
  - It must **not** have the fields `latex`, `mathjson`, `correct`, `misconceptions`, `review` or `answer`.

- [ ] **Step 1: Write the failing tests.** Each example below is one test, parametrised where it's a list.

```python
# test_content_schema.py  (VALID = a dict of a minimal valid compiled expression problem)
def test_valid_problem_parses(): Problem.model_validate(VALID)
def test_unknown_field_rejected():           # review focus 3
    bad = deep_set(VALID, "answer.strict_domian", True)
    assert "strict_domian" in str(raises(ValidationError, Problem.model_validate, bad))
@parametrize("iv", [["1", "0", "open", "open"], ["-inf", "0", "closed", "open"], ["a", "1", "open", "open"]])
def test_bad_interval_rejected(iv): ...
def test_exclude_outside_domain_rejected(): ...
def test_choice_correct_must_be_a_choice_id(): ...
def test_numeric_requires_precision(): ...
def test_precision_forbidden_on_expression(): ...
def test_human_verified_requires_reviewer(): ...
def test_non_openstax_url_rejected(): ...

# test_api_contracts.py
@parametrize("path", glob("contracts/examples/submit-*.json"))
def test_submit_examples_parse(path): SubmissionRequest.model_validate_json(read(path))
@parametrize("path", glob("contracts/examples/item-*.json"))
def test_item_examples_parse(path): PublicItem.model_validate_json(read(path))
@parametrize("mutate", [kind_matrix, uuid_v1, choice_id_upper, choice_with_mathjson, extra_field])
def test_invalid_submissions_rejected(mutate): ...
def test_public_item_has_no_private_fields():
    assert not {"latex", "mathjson", "correct", "misconceptions", "review", "answer"} & set(PublicItem.model_fields)
```

- [ ] **Step 2:** Run `uv run pytest tests/unit -q`. Expected: FAIL (the modules don't exist).
- [ ] **Step 3: Implement the enums and models** in the files listed above.
  - Use the field rules above and `ConfigDict(extra="forbid", frozen=True)`.
  - Don't put validation logic in `domain.py`.
- [ ] **Step 4: Write the example JSON files.**
  - The MathJSON in them is copied from `captured.json` (`six_x_cos`, `dec_0785`).
  - `contracts/README.md` says what each file is for, and that the milestone B browser tests post these same files.
- [ ] **Step 5:** Run `uv run pytest -q && uv run mypy src`. Expected: PASS, with strict mypy clean on `domain` and `content`.
- [ ] **Step 6: Commit** with the message `feat: domain enums, content schema and API contracts`.
