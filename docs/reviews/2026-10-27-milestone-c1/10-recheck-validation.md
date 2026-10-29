# C1 recheck: validation evidence

[Recheck](07-recheck.md) · [Original validation](04-validation-and-next-steps.md)

Date: 2026-10-28. Source HEAD: `b16a206`, branch `milestone-c1`.
This pass updates Markdown only; the saved recheck probe file predates this continuation.
This is pre-fix evidence; the later [debugging pass](11-debugging-fixes.md) owns current results.

## Fresh checks

| Check | Result |
|---|---|
| Focused Python suite below | 595 passed, 1 environment-dependent failure; 110.27 s |
| Isolated `test_settings_defaults` | 1 passed after removing the inherited API-key variable from that command's environment |
| `npm test --prefix tools` | 48 passed |
| Saved recheck probes, `--runxfail --tb=short` | 2 intended failures: C1-R4 and C1-R7; 11.11 s |

The focused Python run covers all `tests/unit/help`, guard/API/race integrations, help
store models and Dockerfile layout tests. The single failure expected an unset key while
the process inherited a configured value; pytest masked it. No credential was printed or
used for a real provider call. Its isolated rerun passed; this is not a fresh all-green CI run.

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/help tests/integration/test_guard_pool.py tests/integration/test_help_api.py tests/integration/test_help_races.py tests/unit/store/test_help_models.py tests/unit/test_dockerfile.py -q --tb=short
.venv\Scripts\python.exe -m pytest docs/reviews/2026-10-27-milestone-c1/test_recheck_probes.py -q --runxfail --tb=short
npm test --prefix tools
```

The first sandboxed attempts encountered temporary-directory/cache permissions. An approved
rerun supplied the focused results above. A server restart lost one earlier run's final output;
only the completed repeat is counted. Sandbox setup errors are not application regressions.

## Documentation verification

Passed in all three affected worktrees, including new Markdown pages:

| Worktree | Markdown files checked | Maximum lines | Problems |
|---|---|---|---|
| Root `main` | 227 | 100 | 0 |
| `milestone-c1` | 254 | 100 | 0 |
| `milestone-c2` | 256 | 100 | 0 |

Relative file links resolve. `git diff --check` and a separate trailing-whitespace scan
of changed/new Markdown passed. There are 27 changed Markdown files across the three trees.
Reproduce from each worktree:

```powershell
.venv\Scripts\python.exe tools/check_docs.py
git diff --check
```

The documentation checker enforces at most 100 lines per Markdown file and relative file
links. It excludes nested worktrees, so the root checkout and C1/C2 must be checked separately.
It does not validate external URLs or heading fragments. New pages require the same
line/whitespace checks as tracked edits.

## Evidence limits

- No fresh full Python suite, lint/type pass, verifier benchmark, browser run or CI claim.
- No actual holdout, paid inference, provider compatibility/pricing check or deployment.
- No production-image smoke or container memory measurement; these remain owner gates.
- No C2 plan-review verdict. Its recorded owner decisions remain intact; implementation
  depends on closing C1-R4/R7 and carrying the fixes into that branch.
