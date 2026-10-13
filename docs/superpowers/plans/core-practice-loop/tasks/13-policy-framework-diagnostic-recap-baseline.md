[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 645–696. Review findings remain unresolved.

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

<!-- End preserved source. -->
