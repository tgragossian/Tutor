"""The bounded verifier pool: deadline, respawn, queue limits and worker reaping (spec 05)."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import psutil
import pytest
from support.checks import boom, die, die_after_reply, ok, sleepy, slow

from mathtutor.content.loader import load_bundle
from mathtutor.verify import pool as pool_module
from mathtutor.verify.pool import VerifierPool
from mathtutor.verify.types import CheckRequest, CheckResult, SubmittedAnswer, Verdict, VerifierBusy

ROOT = Path(__file__).resolve().parents[2]
SEED = load_bundle(ROOT / "content" / "compiled" / "problems.json").bundle.problems
SPEC = next(p.answer for p in SEED if p.answer.kind == "expression")
REQ = CheckRequest(SPEC, SubmittedAnswer(SPEC.kind, SPEC.mathjson, SPEC.latex, None), "req-1")

TIMEOUT = Verdict("unable_to_verify", "timeout", "none")
INTERNAL_ERROR = Verdict("unable_to_verify", "internal_error", "none")


@pytest.fixture
def make_pool() -> Iterator[Callable[..., VerifierPool]]:
    pools: list[VerifierPool] = []

    def make(**kwargs: Any) -> VerifierPool:
        pool = VerifierPool(**kwargs)
        pools.append(pool)
        return pool

    yield make
    for pool in pools:
        pool.close()


def wait_until(condition: Callable[[], bool], timeout: float = 10.0) -> None:
    end = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < end, "condition not reached"
        time.sleep(0.01)


def in_background(pool: VerifierPool) -> threading.Thread:
    def call() -> None:
        try:
            pool.submit(REQ)
        except VerifierBusy:
            pass  # expected once the test closes the pool

    thread = threading.Thread(target=call, daemon=True)
    thread.start()
    return thread


def live_workers() -> list[psutil.Process]:
    """Live child processes, excluding multiprocessing's resource tracker (Linux spawn)."""
    workers = []
    for child in psutil.Process().children(recursive=True):
        try:
            if child.status() == psutil.STATUS_ZOMBIE:
                continue
            if "resource_tracker" in " ".join(child.cmdline()):
                continue
        except psutil.NoSuchProcess:
            continue
        workers.append(child)
    return workers


def zombies() -> list[psutil.Process]:
    found = []
    for child in psutil.Process().children(recursive=True):
        try:
            if child.status() == psutil.STATUS_ZOMBIE:
                found.append(child)
        except psutil.NoSuchProcess:
            pass
    return found


def test_timeout_then_same_pool_recovers(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(check_fn=sleepy, deadline_s=0.5)
    started = time.monotonic()
    assert p.submit(REQ).outcome == TIMEOUT
    assert time.monotonic() - started < 5.0
    p._check_fn_for_test(ok)
    assert p.submit(REQ).outcome.status == "correct"
    assert p.alive()


def test_death_is_internal_error_and_recovers(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(check_fn=die)
    assert p.submit(REQ).outcome == INTERNAL_ERROR
    p._check_fn_for_test(ok)
    assert p.submit(REQ).outcome.status == "correct"
    assert p.alive()


def test_exception_is_internal_error_and_recovers(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(check_fn=boom)
    assert p.submit(REQ).outcome == INTERNAL_ERROR
    p._check_fn_for_test(ok)
    assert p.submit(REQ).outcome.status == "correct"


def test_queue_full_raises_busy_fast(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=1, queue_max=2, queue_wait_s=30.0, deadline_s=30.0, check_fn=sleepy)
    in_background(p)
    wait_until(lambda: p._busy == 1)
    in_background(p)
    in_background(p)
    wait_until(lambda: p._waiting == 2)
    started = time.monotonic()
    with pytest.raises(VerifierBusy):
        p.submit(REQ)
    assert time.monotonic() - started < 0.2


def test_queue_wait_exceeded_raises_busy(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=1, queue_wait_s=0.3, check_fn=slow)
    in_background(p)
    wait_until(lambda: p._busy == 1)
    started = time.monotonic()
    with pytest.raises(VerifierBusy):
        p.submit(REQ)
    assert 0.25 <= time.monotonic() - started < 1.5


def test_sixteen_threads_no_deadlock_no_zombies(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=1, check_fn=slow)
    outcomes: list[object] = []
    lock = threading.Lock()

    def call() -> None:
        try:
            result: object = p.submit(REQ)
        except VerifierBusy as busy:
            result = busy
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=call, daemon=True) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10.0)
    assert not any(t.is_alive() for t in threads), "a caller is still blocked after 10 s"
    assert len(outcomes) == 16
    assert all(isinstance(o, CheckResult | VerifierBusy) for o in outcomes)
    assert any(isinstance(o, CheckResult) for o in outcomes)
    assert len(live_workers()) == 1
    assert zombies() == []


def test_close_reaps_all_workers(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=2, check_fn=ok)
    assert len(live_workers()) == 2
    p.close()
    assert live_workers() == []
    assert zombies() == []
    assert not p.alive()
    with pytest.raises(VerifierBusy):
        p.submit(REQ)


def test_close_while_callers_wait_never_hangs(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=1, queue_wait_s=30.0, check_fn=sleepy)
    outcomes: list[object] = []

    def call() -> None:
        try:
            outcomes.append(p.submit(REQ).outcome)
        except VerifierBusy as busy:
            outcomes.append(busy)

    threads = [threading.Thread(target=call, daemon=True) for _ in range(3)]
    for t in threads:
        t.start()
    wait_until(lambda: p._busy == 1 and p._waiting == 2)
    p.close()
    for t in threads:
        t.join(5.0)
    assert not any(t.is_alive() for t in threads)
    assert sorted(type(o).__name__ for o in outcomes) == ["Verdict", "VerifierBusy", "VerifierBusy"]
    assert INTERNAL_ERROR in outcomes
    assert live_workers() == []


def test_alive_false_after_worker_killed_externally(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=1, check_fn=ok)
    assert p.alive()
    for worker in live_workers():
        worker.kill()
        worker.wait(5)
    assert not p.alive()


def test_timings_recorded(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(check_fn=slow)
    r = p.submit(REQ)
    assert r.worker_ms >= 900 and r.queue_ms >= 0


@pytest.mark.skipif(sys.platform != "linux", reason="RLIMIT_AS is applied on Linux only")
def test_memory_limit_applied_on_linux(make_pool: Callable[..., VerifierPool]) -> None:
    make_pool(size=1, check_fn=ok)
    (worker,) = live_workers()
    assert worker.rlimit(psutil.RLIMIT_AS) == (384 * 2**20, 384 * 2**20)


def test_real_check_through_pool(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool()
    r = p.submit(REQ)
    assert r.outcome.status == "correct"
    assert r.verifier_version


def test_worker_ms_excludes_reap_and_respawn(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(check_fn=sleepy, deadline_s=0.05)
    r = p.submit(REQ)
    assert r.outcome == TIMEOUT
    assert r.worker_ms < 50 + 250


def test_default_check_gets_soft_budget_inside_hard_deadline() -> None:
    from mathtutor.verify.check import check

    fn = pool_module._default_check(3.0)
    assert fn.func is check and fn.keywords == {"deadline_s": 2.5}
    assert pool_module._default_check(0.6).keywords == {"deadline_s": 0.3}


def fail_respawns(p: VerifierPool, times: int, delay: float = 0.0) -> None:
    real = p._new_worker
    left = [times]

    def flaky() -> Any:
        time.sleep(delay)
        if left[0] > 0:
            left[0] -= 1
            raise OSError("injected respawn failure")
        return real()

    p._new_worker = flaky  # type: ignore[method-assign]


def test_failed_respawn_is_retried_by_next_submit(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=1, check_fn=sleepy, deadline_s=0.3)
    fail_respawns(p, 1)
    assert p.submit(REQ).outcome == TIMEOUT
    p._check_fn_for_test(ok)
    assert p.submit(REQ).outcome.status == "correct"
    assert p.alive()
    assert len(live_workers()) == 1


def test_failed_respawn_is_retried_by_alive(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=1, check_fn=sleepy, deadline_s=0.3)
    fail_respawns(p, 2)
    assert p.submit(REQ).outcome == TIMEOUT
    assert not p.alive()  # the retry failed too
    assert p.alive()  # the next retry succeeds
    p._check_fn_for_test(ok)
    assert p.submit(REQ).outcome.status == "correct"


def test_alive_stays_true_during_respawn(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=1, check_fn=sleepy, deadline_s=0.3)
    fail_respawns(p, 0, delay=1.0)
    in_background(p)
    wait_until(lambda: p._respawning == 1)
    assert p.alive()


def test_worker_that_died_after_replying_is_not_reused(
    make_pool: Callable[..., VerifierPool],
) -> None:
    p = make_pool(size=1, check_fn=die_after_reply)
    assert p.submit(REQ).outcome.status == "correct"
    time.sleep(0.5)  # the worker exits 0.1 s after replying
    p._check_fn_for_test(ok)
    assert p.submit(REQ).outcome.status == "correct"


def test_pipe_closed_when_process_start_fails(make_pool: Callable[..., VerifierPool]) -> None:
    p = make_pool(size=1, check_fn=ok)
    real_ctx = p._ctx
    pipes: list[Any] = []

    class BrokenProcess:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def start(self) -> None:
            raise OSError("injected start failure")

    class Ctx:
        def Pipe(self) -> Any:  # noqa: N802
            ends = real_ctx.Pipe()
            pipes.extend(ends)
            return ends

        Process = BrokenProcess

    p._ctx = Ctx()  # type: ignore[assignment]
    with pytest.raises(OSError):
        p._new_worker()
    assert pipes and all(c.closed for c in pipes)


def test_partial_startup_stops_workers_already_created() -> None:
    created: list[Any] = []
    real = VerifierPool._new_worker

    def second_fails(self: VerifierPool) -> Any:
        if created:
            raise OSError("injected second start failure")
        created.append(real(self))
        return created[0]

    with patch.object(VerifierPool, "_new_worker", second_fails):
        with pytest.raises(OSError, match="second start"):
            VerifierPool(size=2, check_fn=ok)
    assert created and created[0]._stopped
    assert live_workers() == []


IMPORT_GATE = """
import sys
from mathtutor.verify import pool as pool_module
from mathtutor.verify.pool import VerifierPool
pool = VerifierPool(size=1)
pool.close()
bad = sorted(n for n in sys.modules if n.split(".")[0] in ("sympy", "mpmath")
             or n == "mathtutor.verify.check")
print(bad)
sys.exit(1 if bad else 0)
"""


def test_pool_keeps_sympy_out_of_parent() -> None:
    result = subprocess.run(
        [sys.executable, "-c", IMPORT_GATE], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
