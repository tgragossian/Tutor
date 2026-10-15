# Task 7: Verifier pool

[Milestone B plan](../README.md) · [Spec 05](../../../../specs/2026-10-13-portfolio-core/05-verifier-execution.md)

**Files:**
- Create: `src/mathtutor/verify/pool.py`, `tests/integration/test_pool.py`, `tests/support/checks.py`
- Modify: `pyproject.toml` (`uv add psutil`)

**Interfaces:**
- Consumes: `check`, `CheckRequest`, `CheckResult`, `VerifierBusy`, `Verdict` (tasks 2, 5).
- Produces (exact signature from spec 05):

```python
class VerifierPool:
    def __init__(self, size: int = 1, deadline_s: float = 3.0, queue_max: int = 8,
                 queue_wait_s: float = 2.0, memory_mb: int | None = 384,
                 check_fn: Callable[[CheckRequest], CheckResult] = check) -> None: ...
    def submit(self, req: CheckRequest) -> CheckResult: ...   # raises VerifierBusy
    def alive(self) -> bool: ...                              # every worker process is running (for /readyz)
    def close(self) -> None: ...
```

- `tests/support/checks.py` holds module-level (picklable) check functions: `sleepy(req)` sleeps 10 s; `die(req)` calls `os._exit(1)`; `slow(req)` sleeps 1 s then returns correct; `ok(req)` returns correct immediately.

- [ ] **Step 1: Write the failing tests.**

```python
def test_timeout_then_same_pool_recovers():
    p = VerifierPool(check_fn=sleepy, deadline_s=0.5)
    assert p.submit(REQ).outcome == Verdict("unable_to_verify", "timeout", "none")
    p._check_fn_for_test(ok); assert p.submit(REQ).outcome.status == "correct"   # same instance
def test_death_is_internal_error_and_recovers(): ...       # die → internal_error; then a normal request succeeds
def test_queue_full_raises_busy_fast(): ...                 # size 1, queue_max 2, slow: 1 running + 2 queued; 4th submit raises VerifierBusy in < 0.2 s
def test_queue_wait_exceeded_raises_busy(): ...             # queue_wait_s 0.3 with a slow job ahead → VerifierBusy after ≈ 0.3 s
def test_sixteen_threads_no_deadlock_no_zombies():
    # 16 threads × submit on size-1 pool with slow; each gets CheckResult or VerifierBusy within 10 s;
    # afterwards psutil.Process().children(recursive=True) has exactly `size` live, non-zombie workers
def test_close_reaps_all_workers(): ...
def test_timings_recorded(): r = pool.submit(REQ); assert r.worker_ms >= 0 and r.queue_ms >= 0
def test_memory_limit_applied_on_linux(): ...               # skipif not linux: worker's resource.getrlimit(RLIMIT_AS) == 384 MB
def test_real_check_through_pool(): ...                     # default check_fn grades a seed answer correct
```

- [ ] **Step 2:** Run `uv run pytest tests/integration/test_pool.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement.**
  - `multiprocessing.get_context("spawn")`; each worker owns a `Pipe`; the worker loop receives `(fn, req)`, runs it, sends the result. On Linux the worker sets `resource.setrlimit(RLIMIT_AS, (memory_mb·2²⁰,)*2)` before its loop.
  - A `threading.BoundedSemaphore`-style admission: at most `queue_max` waiting callers; a caller that cannot get a worker within `queue_wait_s` raises `VerifierBusy`. A caller that cannot even enter the queue raises immediately.
  - `submit` sends the request and `poll(remaining_deadline)`; on timeout: `terminate()`, `join(1)`, `kill()` if still alive, `join()`, respawn, return `unable_to_verify/timeout`. On `EOFError`/`BrokenPipeError` or a dead process: reap, respawn, return `internal_error`. Log both with `req.request_id`.
  - `worker_ms` from dispatch to result; `queue_ms` from `submit` entry to dispatch.
  - `_check_fn_for_test` swaps the function without replacing workers (the function is sent with every job, so this is just an attribute).
  - Wording: comments and docs say "resource containment", never "sandbox" (spec 05).
- [ ] **Step 4:** Run `uv run pytest tests/integration/test_pool.py -q` three times in a row. Expected: PASS every time (no flakes). Then `uv run pytest -q`.
- [ ] **Step 5: Commit** `feat: bounded verifier pool with deadline, respawn and queue limits`.
