"""Module-level (picklable) check functions for driving the verifier pool in tests."""

from __future__ import annotations

import os
import threading
import time

from mathtutor.domain import Method, VerdictReason, VerdictStatus
from mathtutor.verify.types import CheckRequest, CheckResult, Verdict

CORRECT = Verdict(VerdictStatus.CORRECT, VerdictReason.PROVEN, Method.SYMBOLIC)


def ok(req: CheckRequest) -> CheckResult:
    return CheckResult(CORRECT, "test")


def slow(req: CheckRequest) -> CheckResult:
    time.sleep(1.0)
    return CheckResult(CORRECT, "test")


def sleepy(req: CheckRequest) -> CheckResult:
    time.sleep(10.0)
    return CheckResult(CORRECT, "test")


def die(req: CheckRequest) -> CheckResult:
    os._exit(1)


def boom(req: CheckRequest) -> CheckResult:
    raise RuntimeError("check function failed")


def die_after_reply(req: CheckRequest) -> CheckResult:
    threading.Timer(0.1, os._exit, args=(1,)).start()
    return CheckResult(CORRECT, "test")
