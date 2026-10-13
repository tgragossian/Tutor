[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 406–444. Review findings remain unresolved.

### Task 7: Sandboxed verifier pool

**Files:**
- Create: `src/mathtutor/verify/sandbox.py`, `tests/verify/test_sandbox.py`, `tests/verify/slow_checks.py` (module-level `sleep_forever(spec, mj, latex)` and `explode(spec, mj, latex)` for spawn)

**Interfaces:**
- Produces: `class VerifierPool`
  - `__init__(self, size: int = 2, timeout_s: float = 3.0, memory_mb: int = 512, check_fn: Callable[[AnswerSpec, Any, str], Verdict | FormatIssue] = check)`
  - `check(self, spec: AnswerSpec, mathjson: Any, latex: str) -> Verdict | FormatIssue`
  - `close(self) -> None`
  - It is also a context manager.
- How it works:
  - Each worker is a `multiprocessing` spawn-context `Process` with a `Pipe`. Callers take a free worker from a `queue.Queue`.
  - On timeout, the worker is terminated, respawned, and the caller gets `Verdict("unable_to_verify", "timeout", "none", ms)`.
  - On a worker exception → `internal_error`, logged.
  - On Linux the worker calls `resource.setrlimit(RLIMIT_AS, memory_mb MB)` at startup.
  - The pool is thread-safe, because FastAPI calls it from its threadpool.

- [ ] **Step 1: Write the failing tests**

```python
def test_passthrough():
    with VerifierPool(size=1) as p: assert p.check(AnswerSpec("numeric", "3"), mj("num_3"), "3").status == "correct"
def test_timeout_then_recovers():
    with VerifierPool(size=1, timeout_s=0.5, check_fn=sleep_forever) as p:
        v = p.check(AnswerSpec("numeric", "3"), 3, "3"); assert (v.status, v.reason) == ("unable_to_verify", "timeout")
    # second call on a respawned worker with the real check succeeds:
    with VerifierPool(size=1) as p: assert p.check(AnswerSpec("numeric", "3"), mj("num_3"), "3").status == "correct"
def test_exception_is_internal_error(): ...      # explode → reason "internal_error"
def test_concurrent_calls(): ...                 # 8 threads, size=2 → all correct
```

- [ ] **Step 2:** Run `uv run pytest tests/verify/test_sandbox.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `VerifierPool` as described above.
- [ ] **Step 4:** Rerun the tests. Expected: PASS (on Windows the memory limit is skipped).
- [ ] **Step 5: Commit** `feat(verify): sandboxed verifier pool with timeout`.

---

<!-- End preserved source. -->
