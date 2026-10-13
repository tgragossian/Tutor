[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 556–607. Review findings remain unresolved.

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

<!-- End preserved source. -->
