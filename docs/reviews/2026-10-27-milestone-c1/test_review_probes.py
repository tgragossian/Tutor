"""Retired pre-fix C1 probes (original evidence: git b16a206 and review pages 01-04).

These modeled the old Dockerfile, an always-NO_MATCH fake guard, and run.json spend.
Current regressions live in tests/unit/test_dockerfile.py, tests/unit/help/,
tests/integration/test_guard_pool.py and tools/web/help_panel.test.mjs.
The two follow-up reproductions remain in test_recheck_probes.py without xfails.
See 11-debugging-fixes.md for current validation; this module has no active tests.
"""
