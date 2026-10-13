[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 487–511. Review findings remain unresolved.

### Task 9: Seed content (developer-authored)

Most of this is your writing, not code. Tests define what "done" means.

**Files:**
- Create: `content/problems/*.yaml` (one file per area), `content/formulas/*.yaml`, `docs/content-authoring.md` (the §4.3 rubric, the field guide, and "facts not wording" for cheat sheets), `tests/content/test_seed_content.py`

**Interfaces:**
- Consumes: `load_content`.

- [ ] **Step 1: Write the failing tests:**
  - ≥ 20 problems, all `human_verified`
  - every topic has ≥ 1 problem
  - every `answer_type` is used ≥ 1 time
  - every topic has ≥ 5 `recall` and ≥ 2 `concept` items
  - every recall item has `memorize` set
  - each topic has ≥ 1 `core` recall item
  - every source `url` starts with `https://openstax.org/`, and `license == "CC BY-NC-SA 4.0"`
- [ ] **Step 2:** Run `uv run pytest tests/content/test_seed_content.py -v`. Expected: FAIL.
- [ ] **Step 3:** Author the content from OpenStax Vol. 1 using the rubric. `load_content` self-checks every expected answer.
- [ ] **Step 4:** Rerun the tests plus `uv run pytest tests/content -v`. Expected: PASS.
- [ ] **Step 5: Commit** `content: seed problems and formula/concept items for 15 topics`.

---

<!-- End preserved source. -->
