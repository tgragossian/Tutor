[Index](../2026-10-13-core-practice-loop.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 54–63. Review findings remain unresolved.

## Review Focus

1. **Domain-limited "identities."** Student `√(x²)` for expected `x`, and student `2 ln x` for expected `ln(x²)`, agree only on part of ℝ. On a domain that includes negatives both must be judged `incorrect`, never `correct`. *(Test in Task 4.)*
2. **Incomplete MathLive input.** An empty placeholder or an `Error` node (for example the student typed `x^` and stopped) must give a format message ("incomplete expression"). It must not be a verdict and must not create an attempt. *(Tests in Tasks 3 and 5.)*
3. **Sparse content.** 20 seed problems cover 15 topics, so practice will often find no problem at the target difficulty, or none unseen. The policy must fall back in this order: nearest difficulty → seen-but-incorrect → next weakest selected topic → `done` with a reason. It must never raise or loop. *(Test in Task 14.)*
4. **Time budget expires mid-problem.** A submission for the item already on screen is still graded, and `next` then returns `done`. *(Tests in Tasks 14 and 16.)*
5. **Double-submit after an item is finished** (a double-click, or a resubmit after "Show answer") must return `409`. It must not create a second attempt or shift mastery. *(Test in Task 16.)*

---

<!-- End preserved source. -->
