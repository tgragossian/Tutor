"""The load-test helper's pure parts; the burst itself runs against a live server."""

from __future__ import annotations

from pathlib import Path

import pytest
from load.submit_burst import find_target, graded, percentile, session_cookie, summarize

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


def test_database_busy_is_not_expected_backpressure() -> None:
    """Review B-R4: only 503 verifier_busy is the expected queue-full reply."""
    _, unexpected = summarize([(503, "database_busy", 5000.0)] * 16)
    assert unexpected == 16


def test_format_internal_and_transport_replies_are_unexpected() -> None:
    results = [
        (200, "incorrect", 100.0),
        (200, "unable_to_verify", 3000.0),
        (200, "format:incomplete", 5.0),
        (500, "internal_error", 5.0),
        (0, "transport:timed out", 60000.0),
    ]
    text, unexpected = summarize(results)
    assert unexpected == 3
    assert "0 transport:timed out: 1" in text


def test_a_sizing_run_needs_graded_work() -> None:
    assert graded([(503, "verifier_busy", 2000.0)] * 16) == 0
    assert graded([(200, "incorrect", 1.0), (200, "format:empty", 1.0)]) == 1


def test_main_fails_when_nothing_was_graded(monkeypatch: pytest.MonkeyPatch) -> None:
    import load.submit_burst as burst

    monkeypatch.setattr(burst, "register", lambda client, name: None)
    monkeypatch.setattr(burst, "open_at_target", lambda client, target: {})
    monkeypatch.setattr(burst, "burst", lambda clients, target: [(503, "verifier_busy", 1.0)])
    assert burst.main(["--base-url", "http://x", "--users", "1"]) == 1
    monkeypatch.setattr(burst, "burst", lambda clients, target: [(200, "incorrect", 1.0)])
    assert burst.main(["--base-url", "http://x", "--users", "1"]) == 0
