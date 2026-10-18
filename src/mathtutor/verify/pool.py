"""A bounded pool of verifier worker processes (spec 05).

Process isolation plus a wall-clock deadline and (on Linux) an address-space cap is resource
containment, not a security boundary: untrusted input is made safe by the allowlist translator.

The web process imports this module, so it must never import SymPy, mpmath or
``mathtutor.verify.check``. Workers import the default check function themselves.
"""

from __future__ import annotations

import dataclasses
import functools
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

READY_TIMEOUT_S = 120.0  # a cold SymPy import on a slow dev machine; not part of any deadline
CLOSE_GRACE_S = 10.0
SOFT_MARGIN_S = 0.5  # the default check's own budget ends this long before the hard deadline

TIMEOUT = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.TIMEOUT, Method.NONE)
INTERNAL_ERROR = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.INTERNAL_ERROR, Method.NONE)

_READY = "ready"
_OK = "ok"
_FAILED = "failed"

log = logging.getLogger(__name__)


# -- worker process --------------------------------------------------------------------------


def _default_check(deadline_s: float) -> functools.partial[CheckResult]:
    """The default check with a soft budget inside the hard deadline. Runs in the worker only.

    The margin (0.5 s, or half the deadline when that is shorter) covers unpickling,
    translation and one SymPy step that overruns a between-steps budget check, so a slow
    request returns ``timeout`` itself instead of being killed.
    """
    from mathtutor.verify.check import check

    return functools.partial(check, deadline_s=max(deadline_s / 2, deadline_s - SOFT_MARGIN_S))


def _worker_main(
    conn: Connection, memory_mb: int | None, deadline_s: float, warm_default: bool
) -> None:
    """Run jobs ``(check_fn | None, request)`` one at a time until the pipe closes."""
    if sys.platform == "linux" and memory_mb is not None:
        import resource

        limit = memory_mb * 2**20
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    default: CheckFn | None = _default_check(deadline_s) if warm_default else None
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
                default = default or _default_check(deadline_s)
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

    def __init__(
        self, ctx: SpawnContext, memory_mb: int | None, deadline_s: float, warm_default: bool
    ) -> None:
        self.conn, child = ctx.Pipe()
        try:
            self.proc: SpawnProcess = ctx.Process(
                target=_worker_main,
                args=(child, memory_mb, deadline_s, warm_default),
                name="verifier-worker",
                daemon=True,
            )
            self.proc.start()
        except BaseException:
            self.conn.close()
            child.close()
            raise
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
        try:
            return not self._stopped and not wait([self.proc.sentinel], 0)
        except ValueError:  # stop() closed the process object meanwhile
            return False

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

    A worker that times out, fails or dies is replaced. A replacement that fails to start is
    retried lazily: by the next caller that finds the pool short, or by ``alive()``.
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
        self._respawning = 0  # replacements being started outside the lock
        self._workers: list[_Worker] = []
        self._idle: list[_Worker] = []
        # Workers start here, so their start-up never counts against a request's deadline.
        # Each is recorded as soon as it exists, so a later failure stops every earlier one.
        try:
            for _ in range(size):
                self._workers.append(self._new_worker())
            for w in self._workers:
                w.wait_ready()
        except BaseException:
            for w in self._workers:
                w.stop()
            raise
        self._idle = list(self._workers)

    def _new_worker(self) -> _Worker:
        return _Worker(
            self._ctx, self._memory_mb, self._deadline_s, warm_default=self._check_fn is None
        )

    def _check_fn_for_test(self, fn: CheckFn | None) -> None:
        """Swap the check function; it travels with every job, so workers stay as they are."""
        self._check_fn = fn

    def _short(self) -> bool:
        """Fewer workers than ``size``, counting replacements already starting. Hold the lock."""
        return len(self._workers) + self._respawning < self._size

    def alive(self) -> bool:
        """Every worker process is running (for /readyz). A replacement still starting counts
        as running; a pool left short by a failed replacement retries it here first."""
        with self._cond:
            if self._closed:
                return False
            retry = self._short()
            if retry:
                self._respawning += 1
        if retry:
            self._finish_respawn(self._spawn(), take=False)
        with self._cond:
            if self._closed or self._short():
                return False
            return all(w.running() for w in self._workers)

    def submit(self, req: CheckRequest) -> CheckResult:
        entered = time.monotonic()
        worker = self._acquire(entered)
        dispatched = time.monotonic()
        replace = True
        try:
            outcome, replace = self._run(worker, req)
            finished = time.monotonic()  # before any reap or respawn
        finally:
            self._release(worker, replace)
        worker_ms = int((finished - dispatched) * 1000)
        queue_ms = int((dispatched - entered) * 1000)
        if isinstance(outcome, CheckResult):
            return dataclasses.replace(outcome, worker_ms=worker_ms, queue_ms=queue_ms)
        return CheckResult(outcome, VERIFIER_VERSION, worker_ms=worker_ms, queue_ms=queue_ms)

    def _acquire(self, entered: float) -> _Worker:
        """Check out a live worker, starting a replacement if the pool is short."""
        dead: _Worker | None = None
        with self._cond:
            if self._closed:
                raise VerifierBusy("verifier pool is closed")
            if (not self._idle or self._waiting) and self._waiting >= self._queue_max:
                raise VerifierBusy("verifier queue is full")
            self._waiting += 1
            try:
                give_up = entered + self._queue_wait_s
                while True:
                    if self._closed:
                        raise VerifierBusy("verifier pool is closed")
                    if self._idle:
                        worker = self._idle.pop()
                        if worker.running():
                            self._busy += 1
                            return worker
                        # It died while idle (e.g. right after replying): never reuse it.
                        self._workers.remove(worker)
                        dead = worker
                        self._respawning += 1
                        break
                    if self._short():
                        self._respawning += 1
                        break
                    remaining = give_up - time.monotonic()
                    if remaining <= 0:
                        raise VerifierBusy("verifier queue wait expired")
                    self._cond.wait(remaining)
            finally:
                self._waiting -= 1
        if dead is not None:
            log.error("verifier worker died while idle; replacing it")
            dead.stop()
        new = self._finish_respawn(self._spawn(), take=True)
        if new is None:
            raise VerifierBusy("verifier worker could not be started")
        return new

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
                    return result, not worker.running()  # replied, then died: replace it
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
        """Return the worker, or reap it and start a replacement. The caller owns ``worker``."""
        with self._cond:
            self._busy -= 1
            discard = replace or self._closed
            respawn = discard and not self._closed
            if discard:
                self._workers.remove(worker)
                if respawn:
                    self._respawning += 1
            else:
                self._idle.append(worker)
            self._cond.notify_all()
        if discard:
            worker.stop()
        if respawn:
            self._finish_respawn(self._spawn(), take=False)

    def _spawn(self) -> _Worker | None:
        """Start a worker and wait until it is warm; None if that fails."""
        try:
            new = self._new_worker()
            new.wait_ready()
        except Exception:
            log.exception("verifier worker respawn failed")
            return None
        return new

    def _finish_respawn(self, new: _Worker | None, take: bool) -> _Worker | None:
        """Settle a replacement claimed via ``_respawning``: checked out to the caller if
        ``take`` (and returned), otherwise made idle. A pool that closed meanwhile stops it."""
        with self._cond:
            self._respawning -= 1
            keep = new is not None and not self._closed
            if new is not None and keep:
                self._workers.append(new)
                if take:
                    self._busy += 1
                else:
                    self._idle.append(new)
            self._cond.notify_all()
        if new is not None and not keep:
            new.stop()
            return None
        return new if take else None

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
            self._cond.wait_for(lambda: self._busy == 0 and self._respawning == 0, CLOSE_GRACE_S)
