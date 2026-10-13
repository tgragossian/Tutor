# 05 — Verifier execution

[Contracts index](README.md)

## Process model

- There is one bounded `VerifierPool` per app process, created at startup. It starts with **size 1**; [09](09-operations.md) raises this only after host memory has been measured.
- Each worker is a spawn-context process that runs `translate → pre-checks → equivalence` for one request at a time. Nothing that builds math objects runs in the web process ([03](03-input-bounds.md)).
- **Deadline:** 3 s of wall time per request, measured from dispatch, covering translation and all proof strategies.
  - Each proof strategy gets a sub-budget inside that deadline.
  - Exceeding the deadline → kill the worker, wait for its process to exit (reap it), respawn → `unable_to_verify`, reason `timeout`.
- **Queue:** at most 8 waiting requests, with a maximum queue wait of 2 s.
  - When either limit is exceeded, the API returns 503 `verifier_busy` with `Retry-After: 2`.
  - The submission is **not** recorded as an attempt and the client may resend the same `submission_id`.
- **Memory:** on Linux, `RLIMIT_AS` = 384 MB per worker, adjusted after measurement in [09](09-operations.md). On Windows (development only) the cap is skipped.
- **Crashes:** a worker exception or death → respawn → `unable_to_verify`, reason `internal_error`, logged with the request id.
- **Wording:** process isolation plus limits is **resource containment, not a security sandbox**. The only security boundary for untrusted input is the allowlist translator; code and docs must not call it a sandbox.

## Interface

```python
class VerifierPool:
    def __init__(self, size: int = 1, deadline_s: float = 3.0, queue_max: int = 8,
                 queue_wait_s: float = 2.0, memory_mb: int | None = 384,
                 check_fn: Callable[[CheckRequest], CheckResult] = check) -> None: ...
    def submit(self, req: CheckRequest) -> CheckResult: ...   # raises VerifierBusy
    def close(self) -> None: ...

@dataclass(frozen=True)
class CheckRequest:
    answer_spec: CompiledAnswer          # from content (01)
    answer: SubmittedAnswer              # from the payload (02)

@dataclass(frozen=True)
class CheckResult:
    outcome: Verdict | FormatIssue
    verifier_version: str                # package version + git sha
    worker_ms: int; queue_ms: int
```

## Tests required (milestone B)

- **Same-pool recovery:** a `check_fn` that sleeps → `timeout`. The **same** pool instance then answers a normal request correctly.
- **Death:** a `check_fn` that calls `os._exit(1)` → `internal_error`, and the same pool still recovers.
- **Bounded queue:** fill the queue with slow checks. The next `submit` raises `VerifierBusy` within ~`queue_wait_s`.
- **Concurrency:** 16 threads against a pool of size 1 → every request completes or gets `VerifierBusy`. No deadlocks and no zombie processes, checked with `psutil` in the test.
- **Latency:** recorded separately as worker and queue time. Reported per host ([08](08-verifier-evaluation.md)), not used as a CI gate.
