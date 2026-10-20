"""The eval CLI grades through the verifier pool, so a pathological case cannot hang CI."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from support.checks import sleepy

from mathtutor.content.loader import load_bundle
from mathtutor.verify import evaluate as ev
from mathtutor.verify.pool import VerifierPool

ROOT = Path(__file__).resolve().parents[2]
REAL_PATH = ROOT / "content" / "compiled" / "problems.json"
TINY = ROOT / "tests" / "fixtures" / "evals" / "tiny.jsonl"


def test_slow_case_times_out_without_hanging() -> None:
    cases = ev.load_cases(TINY)[:2]
    pool = VerifierPool(size=1, deadline_s=0.5, check_fn=sleepy)
    try:
        started = time.monotonic()
        metrics, results = ev.evaluate(cases, load_bundle(REAL_PATH), grade=pool.submit)
        elapsed = time.monotonic() - started
    finally:
        pool.close()
    assert elapsed < 8
    assert [r.reason for r in results] == ["timeout", "timeout"]
    assert metrics.abstain["correct"][0] + metrics.abstain["incorrect"][0] == 2


def test_cli_grades_through_a_pool_and_closes_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pools: list[VerifierPool] = []
    real = VerifierPool

    def tracking(**kwargs: object) -> VerifierPool:
        pool = real(**kwargs)  # type: ignore[arg-type]
        pools.append(pool)
        return pool

    monkeypatch.setattr(ev, "VerifierPool", tracking)
    code = ev.main(["--set", "generated", "--cases", str(TINY), "--content", str(REAL_PATH)])
    assert code == 0 and len(pools) == 1
    assert pools[0].alive() is False  # closed on exit
    assert "FA (wrong accepted)" in capsys.readouterr().out
