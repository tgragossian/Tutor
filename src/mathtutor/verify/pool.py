"""A bounded pool of verifier worker processes (spec 05).

Process isolation plus a wall-clock deadline and (on Linux) an address-space cap is resource
containment, not a security boundary: untrusted input is made safe by the allowlist translator.

The web process imports this module, so it must never import SymPy, mpmath or
``mathtutor.verify.check``. Workers resolve the default check function by import path.
"""

from __future__ import annotations

import dataclasses
import importlib
import logging
import multiprocessing
import sys
import threading
import time
from collections.abc import Callable
from multiprocessing.connection import Connection, wait
from multiprocessing.context import SpawnContext, SpawnProcess
from typing import Any

from mathtutor.domain import Method, VerdictReason, VerdictStatus
from mathtutor.verify.types import (
    VERIFIER_VERSION,
    CheckRequest,
    CheckResult,
    Verdict,
    VerifierBusy,
)

CheckFn = Callable[[CheckRequest], CheckResult]

DEFAULT_CHECK = "mathtutor.verify.check:check"
READY_TIMEOUT_S = 120.0  # a cold SymPy import on a slow dev machine; not part of any deadline
CLOSE_GRACE_S = 10.0

TIMEOUT = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.TIMEOUT, Method.NONE)
INTERNAL_ERROR = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.INTERNAL_ERROR, Method.NONE)

_READY = "ready"
_OK = "ok"
_FAILED = "failed"

log = logging.getLogger(__name__)


# -- worker process --------------------------------------------------------------------------


def _resolve(path: str) -> CheckFn:
    module, _, name = path.partition(":")
    fn: CheckFn = getattr(importlib.import_module(module), name)
    return fn


def _worker_main(conn: Connection, memory_mb: int | None, warm_default: bool) -> None:
    """Run jobs ``(check_fn | None, request)`` one at a time until the pipe closes."""
    if sys.platform == "linux" and memory_mb is not None:
        import resource

        limit = memory_mb * 2**20
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    default = _resolve(DEFAULT_CHECK) if warm_default else None
    conn.send(_READY)
    while True:
        try:
            job = conn.recv()
        except EOFError:
            return
        if job is None:
            return
        fn, req = job
        try:
            if fn is None:
                default = default or _resolve(DEFAULT_CHECK)
                fn = default
            reply: tuple[str, Any] = (_OK, fn(req))
        except Exception:
            log.exception("check function failed (request %s)", req.request_id)
            reply = (_FAILED, None)
        conn.send(reply)


class _Worker:
    """One worker process and the parent's end of its pipe.

    Only the thread that has checked the worker out of the pool uses ``conn``.
    """

    def __init__(self, ctx: SpawnContext, memory_mb: int | None, warm_default: bool) -> None:
        self.conn, child = ctx.Pipe()
        self.proc: SpawnProcess = ctx.Process(
            target=_worker_main,
            args=(child, memory_mb, warm_default),
            name="verifier-worker",
            daemon=True,
        )
        self.proc.start()
        child.close()  # so the parent sees EOF when the worker dies
        self._stop_lock = threading.Lock()
        self._stopped = False

    def wait_ready(self) -> None:
        ready = wait([self.conn, self.proc.sentinel], READY_TIMEOUT_S)
        try:
            if self.conn in ready and self.conn.recv() == _READY:
                return
        except (EOFError, OSError):
            pass
        self.stop()
        raise RuntimeError("verifier worker failed to start")

    def running(self) -> bool:
        """True while the process runs. Checks the sentinel, so it never reaps."""
        return not self._stopped and not wait([self.proc.sentinel], 0)

    def signal_stop(self) -> None:
        """Ask the process to exit without touching the pipe (safe from any thread)."""
        with self._stop_lock:
            if not self._stopped:
                self.proc.terminate()

    def stop(self) -> None:
        """Terminate, then kill if needed, reap the process and release its resources."""
        with self._stop_lock:
            if self._stopped:
                return
            self._stopped = True
            self.proc.terminate()
            self.proc.join(1.0)
            if self.proc.is_alive():
                self.proc.kill()
            self.proc.join()
            self.conn.close()
            self.proc.close()


# -- pool ------------------------------------------------------------------------------------


class VerifierPool:
    """Runs ``check_fn`` in worker processes under a deadline, with a bounded wait queue.

    ``queue_max`` counts callers waiting for a worker, not the ones running. A caller that
    finds the queue full, or waits longer than ``queue_wait_s``, gets ``VerifierBusy``.
    """

    def __init__(
        self,
        size: int = 1,
        deadline_s: float = 3.0,
        queue_max: int = 8,
        queue_wait_s: float = 2.0,
        memory_mb: int | None = 384,
        check_fn: CheckFn | None = None,
    ) -> None:
        if size < 1:
            raise ValueError("pool size must be at least 1")
        self._size = size
        self._deadline_s = deadline_s
        self._queue_max = queue_max
        self._queue_wait_s = queue_wait_s
        self._memory_mb = memory_mb
        self._check_fn = check_fn
        self._ctx = multiprocessing.get_context("spawn")
        self._cond = threading.Condition()
        self._closed = False
        self._waiting = 0  # callers waiting for a worker
        self._busy = 0  # workers checked out by a caller
        # Workers start here, so their start-up never counts against a request's deadline.
        workers = [self._new_worker() for _ in range(size)]
        try:
            for w in workers:
                w.wait_ready()
        except BaseException:
            for w in workers:
                w.stop()
            raise
        self._workers: list[_Worker] = workers
        self._idle: list[_Worker] = list(workers)

    def _new_worker(self) -> _Worker:
        return _Worker(self._ctx, self._memory_mb, warm_default=self._check_fn is None)

    def _check_fn_for_test(self, fn: CheckFn | None) -> None:
        """Swap the check function; it travels with every job, so workers stay as they are."""
        self._check_fn = fn

    def alive(self) -> bool:
        """Every worker process is running (for /readyz)."""
        with self._cond:
            if self._closed or len(self._workers) != self._size:
                return False
            return all(w.running() for w in self._workers)

    def submit(self, req: CheckRequest) -> CheckResult:
        entered = time.monotonic()
        worker = self._acquire(entered)
        dispatched = time.monotonic()
        replace = True
        try:
            outcome, replace = self._run(worker, req)
        finally:
            self._release(worker, replace)
        worker_ms = int((time.monotonic() - dispatched) * 1000)
        queue_ms = int((dispatched - entered) * 1000)
        if isinstance(outcome, CheckResult):
            return dataclasses.replace(outcome, worker_ms=worker_ms, queue_ms=queue_ms)
        return CheckResult(outcome, VERIFIER_VERSION, worker_ms=worker_ms, queue_ms=queue_ms)

    def _acquire(self, entered: float) -> _Worker:
        with self._cond:
            if self._closed:
                raise VerifierBusy("verifier pool is closed")
            if not self._idle or self._waiting:
                if self._waiting >= self._queue_max:
                    raise VerifierBusy("verifier queue is full")
                self._waiting += 1
                try:
                    give_up = entered + self._queue_wait_s
                    while not self._idle and not self._closed:
                        remaining = give_up - time.monotonic()
                        if remaining <= 0:
                            raise VerifierBusy("verifier queue wait expired")
                        self._cond.wait(remaining)
                    if self._closed:
                        raise VerifierBusy("verifier pool is closed")
                finally:
                    self._waiting -= 1
            self._busy += 1
            return self._idle.pop()

    def _run(self, worker: _Worker, req: CheckRequest) -> tuple[CheckResult | Verdict, bool]:
        """Run one job. Returns the outcome and whether the worker must be replaced."""
        try:
            worker.conn.send((self._check_fn, req))
        except OSError:
            log.error("verifier worker died before dispatch (request %s)", req.request_id)
            return INTERNAL_ERROR, True
        ready = wait([worker.conn, worker.proc.sentinel], self._deadline_s)
        if worker.conn in ready:
            try:
                tag, result = worker.conn.recv()
            except (EOFError, OSError):
                pass
            else:
                if tag == _OK:
                    return result, False
                log.error("verifier check raised (request %s)", req.request_id)
                return INTERNAL_ERROR, True
        elif not ready:
            log.warning(
                "verifier deadline of %.1f s exceeded (request %s)",
                self._deadline_s,
                req.request_id,
            )
            return TIMEOUT, True
        log.error("verifier worker died (request %s)", req.request_id)
        return INTERNAL_ERROR, True

    def _release(self, worker: _Worker, replace: bool) -> None:
        """Return the worker, or reap it and swap in a fresh one. The caller owns ``worker``."""
        new: _Worker | None = None
        if replace:
            worker.stop()
            if not self._closed:
                try:
                    new = self._new_worker()
                    new.wait_ready()
                except Exception:
                    log.exception("verifier worker respawn failed")
                    new = None
        with self._cond:
            self._busy -= 1
            if replace or self._closed:
                self._workers.remove(worker)
                if new is not None and not self._closed:
                    self._workers.append(new)
                    self._idle.append(new)
                    new = None
            else:
                self._idle.append(worker)
            self._cond.notify_all()
        if new is not None:  # the pool closed while it started
            new.stop()
        if self._closed:
            worker.stop()  # idempotent

    def close(self) -> None:
        """Reap every worker. Waiting callers get ``VerifierBusy``; running ones get
        ``internal_error``. Safe to call more than once and while callers are waiting."""
        with self._cond:
            self._closed = True
            idle, self._idle = self._idle, []
            for w in idle:
                self._workers.remove(w)
            running = list(self._workers)
            self._cond.notify_all()
        for w in idle:
            w.stop()
        for w in running:
            w.signal_stop()  # its caller sees the death, reaps it and does not respawn
        with self._cond:
            self._cond.wait_for(lambda: self._busy == 0, CLOSE_GRACE_S)
