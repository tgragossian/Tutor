[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 445–486. Review findings remain unresolved.

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

<!-- End preserved source. -->
