"""The load-test helper's pure parts; the burst itself runs against a live server."""

from __future__ import annotations

from pathlib import Path

import pytest
from load.submit_burst import find_target, percentile, session_cookie, summarize

ROOT = Path(__file__).resolve().parents[2]


def test_find_target_reads_the_dev_case_and_its_problem() -> None:
    t = find_target(ROOT, "d-181-07")
    assert t.problem_id == "openstax-c1-3.5-181"
    assert t.topic == "derivatives.trig"
    assert (t.section, t.exercise) == ("3.5", 181)
    assert t.answer["kind"] == "expression" and t.answer["mathjson"] and t.answer["latex"]


def test_find_target_keeps_decimals_exact() -> None:
    t = find_target(ROOT, "d-253-01")
    assert "0.583" in str(t.answer["mathjson"]) and "{'num': '" in str(t.answer["mathjson"])


def test_find_target_rejects_unknown_case() -> None:
    with pytest.raises(SystemExit, match="no dev case"):
        find_target(ROOT, "d-nope")


def test_percentile() -> None:
    values = [float(v) for v in range(1, 101)]
    assert percentile(values, 50) == 50.0
    assert percentile(values, 95) == 95.0
    assert percentile([7.0], 95) == 7.0


def test_session_cookie_from_set_cookie_headers() -> None:
    headers = ["other=1; Path=/", "mt_session=abc.def; HttpOnly; Secure; Path=/"]
    assert session_cookie(headers) == "abc.def"
    assert session_cookie(["other=1"]) is None


def test_summarize_counts_outcomes_and_latency() -> None:
    results = [
        (200, "incorrect", 120.0),
        (200, "incorrect", 180.0),
        (503, "verifier_busy", 2010.0),
        (500, "internal_error", 5.0),
    ]
    text, unexpected = summarize(results)
    assert "200 incorrect: 2" in text and "503 verifier_busy: 1" in text
    assert "p50" in text and "max 2010 ms" in text
    assert unexpected == 1
