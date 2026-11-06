# Cleanup: procedure

[Plan](README.md)

Run after Codex's review and Thomas's approval, on its own branch, after `answers-table`
is merged (so the two do not conflict in `handoff.md` and the indexes).

1. **Local clutter** ([01-local.md](01-local.md)): remove the four worktrees, delete
   `%SystemDrive%/` and `.playwright-mcp/`, add `.playwright-mcp/` to `.gitignore`.
2. **Tag:** `git tag archive-2026-11-06` on `main` (push the tag if Codex recommends it).
3. **Move evidence first:** copy any fact Codex marks as still needed (G4 verification
   evidence, G2 still-true facts) into its current home; commit.
4. **Delete** the approved groups from [02-candidates.md](02-candidates.md); commit per group,
   so each is easy to review or revert.
5. **Fix links** in [03-links.md](03-links.md); add `docs/history.md` (≤ 100 lines: group,
   reason, date, how to read it from the tag).
6. **Checks:** `uv run python tools/check_docs.py` (no output), full pytest (G6 removal must
   not drop a collected test), `git grep` for every deleted path returns nothing.
7. **Handoff:** one line in `handoff.md` pointing at `docs/history.md`.
