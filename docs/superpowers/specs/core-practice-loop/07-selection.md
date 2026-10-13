[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 271–328. Review findings remain unresolved.

## 6. Mastery and selection policies

### 6.1 Mastery (per topic, two scores)

- **Recall score:** computed from `recall` and `concept` items.
- **Application score:** computed from `problem` items.
- **Which attempts count:** only first attempts. A `multiple_choice` attempt has weight 0.5; others have weight 1.0. Each attempt is further multiplied by recency decay 0.5^(k/10), where k is the number of newer attempts the user has in that topic and score.
- **Formula:** score = (Σ w·correct + 1) / (Σ w + 2).
- **Bands:**
  - fewer than 2 counted attempts → `not_seen`
  - < 0.5 → `weak`
  - 0.5–0.8 → `shaky`
  - ≥ 0.8 → `strong`
- `unable_to_verify` attempts are excluded from mastery.

### 6.2 Time estimate per problem

Difficulty 1/2/3/4/5 → 1.5/2.5/3.5/4.5/6 minutes. Recall and concept items take 0.5 minutes each.

### 6.3 Exam conditions

| Setting | Recall items used | Formula sheet panel |
|---|---|---|
| `closed_book` | all | hidden |
| `formula_sheet` | `memorize: core` only | available |
| `open_notes` | none (concept items only) | available |

### 6.4 Policies

Every selection returns `(item_id | None, reason: str)`. The reason is shown to the student.

**Diagnostic**
- For each selected topic in textbook order:
  - 1 recall or concept item (filtered by exam conditions)
  - 2 unseen problems at difficulty 2–3
- If the time budget cannot fit that, use 1 problem per topic.
- One try per item and no per-item feedback.
- The session ends with a report: per-topic recall and application bands, plus each item with its verdict. The report has a "Practise my weak topics" button that pre-fills a practice session.

**Practice**
- **Warm-up:** if enabled (the default), up to 6 recall and concept items for the selected topics, weakest recall first. Immediate feedback; skippable.
- **Main loop:**
  1. **Topic:** the selected topic with the lowest application score (`not_seen` counts as 0.5). If one of its prerequisites is `weak`, choose one problem from that prerequisite first. Reason example: "Prerequisite check: derivatives.basic_rules is weak".
  2. **Difficulty:** start at the user's current level for that topic (default 2). +1 after 2 consecutive correct first attempts; −1 after an incorrect one; clamped to 1–5. If no problem exists at that level, use the nearest available level.
  3. **Problem:** unseen first. If all have been seen, choose the one whose most recent attempt was incorrect and oldest.
  4. Up to 3 tries per problem. After that, a "Show answer" button sets `revealed` and moves on.
  5. **Stop:** when the elapsed time reaches `minutes_budget`, after the current item finishes, or when no eligible items remain.

**Recap**
- Recall and concept items for the selected topics, filtered by exam conditions, with immediate feedback.
- Ends with the per-topic formula sheet.

**Textbook-order baseline**
- Topics in `order`, problems by difficulty ascending.
- It has the same interface but is not exposed in the UI. It exists for later policy comparison.

---

<!-- End preserved source. -->
