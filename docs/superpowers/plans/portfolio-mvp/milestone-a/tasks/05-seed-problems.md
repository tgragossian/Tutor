# Task 5: Six seed problems (human-reviewed)

[Milestone A plan](../README.md) · [Spec 01](../../../../specs/2026-10-13-portfolio-core/01-content-and-domains.md)

**Files:**
- Create:
  - `content/problems/*.yaml` (six files, each named `<id>.yaml`)
  - `content/sources/openstax-calculus-v1.md`
  - `tests/unit/test_seed_content.py`
- Modify:
  - `content/compiled/problems.json` (regenerated)
  - `content/README.md` (create it if missing): an index linking the sources manifest and explaining how to author and compile problems
  - `docs/README.md`: link `content/README.md`

**Interfaces:**
- Consumes: the compiler and loader from task 4, and the schema from task 3.
- Produces: the real bundle that tasks 6–8 serve. Milestone B grows it to 20–30 problems.

**Required mix:**
- Two problems per topic.
- At least 4 `expression`, 1 `numeric` (`precision: {decimals: 3}`) and 1 `choice`.
- At least one expression problem whose expected answer has a domain other than ℝ, for example one involving `\sqrt{x}`, `1/x` or `\tan x`.
- At least one problem has `misconceptions`.
- `expression` and `numeric` problems are transcribed from **real** OpenStax Calculus Volume 1 exercises in §3.3, §3.5 or §3.6.
  - `exercise` is the book's exercise number.
  - `url` is the section page.
- The `choice` problem is written by the author, with `source.adapted: true`, `exercise: null`, and the section it's based on.
  - Distractors come from real misconceptions.
- **Authoring rule:** all LaTeX in single-quoted YAML strings (review focus 2).

**`openstax-calculus-v1.md`:** includes:
- book, authors and edition
- the base URL
- the licence `CC BY-NC-SA 4.0`, with a link to the licence
- the attribution sentence shown in the UI
- a note that the adapted items are derivatives of the original and use the same licence

- [ ] **Step 1: Write the failing test** (`test_seed_content.py`, loading the real `content/compiled/problems.json`).

```python
def test_six_problems_two_per_topic(): assert Counter(p.topic for p in problems) == {t: 2 for t in TOPICS}
def test_kind_mix(): k = Counter(p.answer.kind for p in problems); assert k["expression"] >= 4 and k["numeric"] >= 1 and k["choice"] >= 1
def test_some_domain_is_not_all_reals(): assert any(not is_all_reals(p.answer.domain) for p in expr_problems)
def test_urls_match_section(): assert all(f"/pages/3-{p.source.section.split('.')[1]}-" in p.source.url for p in problems)
def test_all_human_verified(): assert all(p.review.status == "human_verified" for p in problems)
```

- [ ] **Step 2:** Run `uv run pytest tests/unit/test_seed_content.py -q`. Expected: FAIL (zero problems).
- [ ] **Step 3: Draft the six YAML files** with `review: {status: needs_review, reviewer: "", date: "", notes: ""}`.
  - For each, put in the notes the reasoning or a worked check, so the expected answer (and the domain where it isn't ℝ) can be verified.
  - Never copy an answer without checking it.
- [ ] **Step 4:** Run `npm run compile --prefix tools`, then the step 1 tests.
  - Expected: everything passes except `test_all_human_verified`.
- [ ] **Step 5: Human gate (Thomas).** For each problem, check against the book:
  - the statement matches the exercise
  - the expected answer is correct (the OpenStax answer key covers the odd exercises)
  - the domain is right
  - each distractor is genuinely wrong

  Then set `status: human_verified`, `reviewer: "tg"` and the date, with any notes. Problems that fail stay `needs_review` and get fixed.
- [ ] **Step 6:** Recompile, then run `uv run pytest -q` and `npm test --prefix tools`.
  - Expected: all pass, including `test_compiled_tools_match_captured_meta`.
- [ ] **Step 7: Commit** with the message `feat: six human-reviewed seed problems`. The commit body lists the six ids.
