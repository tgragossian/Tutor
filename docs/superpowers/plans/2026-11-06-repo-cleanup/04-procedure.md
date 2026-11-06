# Cleanup: executed steps and recovery

[Plan](README.md) · [Disposition](../../../reviews/2026-11-06-repo-cleanup/README.md)

1. Tagged the clean pre-cleanup `answers-table` head `f9a9cbc` as
   `archive-2026-11-06` (local tag).
2. Removed G1's 40 superseded Markdown files and the empty C1 original probe stub.
3. Added [history](../../../history.md), repaired inbound Markdown links, and recorded
   the group-by-group keep decisions in the review.
4. Ran `tools/check_docs.py` and `git diff --check`; both passed.

To inspect any deleted file:

```text
git show archive-2026-11-06:<path>
git show f9a9cbc:<path>
```

The branch remains unmerged. The tag is local. The worktrees and untracked browser
output remain untouched; they require a separate, fresh inspection before removal.
