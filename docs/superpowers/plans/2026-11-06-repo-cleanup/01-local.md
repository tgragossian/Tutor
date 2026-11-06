# Cleanup: local clutter (not in git)

[Plan](README.md)

These live only in Thomas's working folder, so removing them changes no commit. They are
the likeliest source of AI confusion: each worktree is a full old copy of the repo.

| Path | Size | State (2026-11-06) | Proposal |
|---|---|---|---|
| `.claude/worktrees/milestone-a` | ~190 MB | 1 docs commit not on `main`, pushed to GitHub | remove worktree; keep branch |
| `.claude/worktrees/milestone-b` | ~200 MB | 1 docs commit not on `main`, pushed | remove worktree; keep branch |
| `.claude/worktrees/milestone-c1` | ~365 MB | fully merged into `main` | remove worktree; branch may go too |
| `.claude/worktrees/milestone-c2` | ~12 MB | open C2 work, 11 commits, pushed | remove worktree; recreate when C2 resumes |
| `.claude/worktrees/answers-table` | ~340 MB | awaiting Codex review | keep until merged |
| `%SystemDrive%/` (repo root) | <1 MB | Windows cache files created by a literal `%SystemDrive%` path; untracked | delete |
| `.playwright-mcp/` | small | browser-tool output; untracked | delete and add to `.gitignore` |

Command per worktree (keeps the branch): `git worktree remove .claude/worktrees/<name>`.

Optional: if an AI tool Thomas uses supports an ignore file, list `.claude/worktrees/`,
`.venv/`, caches and `evals/help/results/*/` raw files there (check each tool's docs for the
filename).
