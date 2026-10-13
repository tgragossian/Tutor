[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 697–738. Review findings remain unresolved.

### Task 14: Practice policy

**Files:**
- Create: `src/mathtutor/recommend/practice.py`, `tests/recommend/test_practice.py`
- Modify: `policy_for` (wire `practice`)

**Interfaces:**
- Produces: `class PracticePolicy(Policy)`, plus `def current_level(attempts: Sequence[AttemptRecord], bank: ContentBank, topic: str) -> int`. The level replays the user's first-attempt problem history in that topic: start at 2, +1 after 2 consecutive correct, −1 on incorrect, clamped to 1–5.
- **Order of checks:**
  1. **Time:** if `now − session_started_at ≥ minutes_budget` → `None`, reason "time budget reached".
  2. **Warm-up:** if `plan.warmup_enabled`, fewer than 6 recall or concept attempts in the session, and an eligible item not yet attempted in the session exists → choose the one with the lowest recall score (ties broken by id). Reason "Warm-up: …".
  3. **Topic:** the selected topic with the lowest application score. If a prerequisite (in the full graph) is `weak` and has servable problems, use the prerequisite instead. Reason "Prerequisite check: <topic> is weak".
  4. **Problem, with fallbacks (Review Focus 3):**
     1. unseen problems at `current_level`
     2. unseen at the nearest level (ties go lower)
     3. seen problems whose latest attempt was incorrect, oldest first
     4. repeat for the next-weakest selected topic
     5. `None`, reason "no more problems available for the selected topics"

- [ ] **Step 1: Write the failing tests:**

```python
def test_warmup_first_then_problems(): ...
def test_warmup_capped_at_6(): ...
def test_warmup_disabled_skips(): ...
def test_weakest_topic_chosen(): ...
def test_prerequisite_check_reason(): ...         # reason starts with "Prerequisite check:"
def test_level_up_after_two_correct(): assert current_level([...c, c], bank, "t") == 3
def test_level_down_and_clamp(): ...
def test_nearest_difficulty_fallback(): ...       # only difficulty-5 problems exist, level 2 → picks the 5
def test_seen_incorrect_fallback(): ...
def test_exhausted_returns_none_with_reason(): ... # Review Focus 3 — never raises
def test_time_budget_reached(): ...               # Review Focus 4 — now = start + budget → None
```

- [ ] **Step 2:** Run `uv run pytest tests/recommend/test_practice.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `uv run pytest tests/recommend -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(recommend): adaptive practice policy with warm-up`.

---

<!-- End preserved source. -->
