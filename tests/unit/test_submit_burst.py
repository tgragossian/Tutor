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


def _crash() -> dict[str, object]:
    return {"status": "unable_to_verify", "reason": "internal_error", "method": "none"}


def _verdict(status: str, reason: str) -> dict[str, object]:
    return {"status": status, "reason": reason, "method": "refutation"}


def _run_burst(monkeypatch: pytest.MonkeyPatch, outcomes: list[dict[str, object]]) -> int:
    """The real burst/summary/CLI path with HTTP and setup stubbed (review recheck B-R4)."""
    import load.submit_burst as burst

    replies = iter(outcomes)
    lock = __import__("threading").Lock()

    def call(self: object, method: str, path: str, body: object = None) -> tuple:
        with lock:
            return 200, {"outcome": next(replies)}, []

    monkeypatch.setattr(burst.Client, "call", call)
    monkeypatch.setattr(burst, "register", lambda client, name: None)
    item = {"session_item_id": 1, "revision": 0}
    monkeypatch.setattr(
        burst, "open_at_target", lambda client, target: {"session_id": 1, "item": item}
    )
    return burst.main(["--base-url", "http://unused.invalid", "--users", str(len(outcomes))])


def test_verifier_crashes_under_http_200_fail_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _run_burst(monkeypatch, [_crash(), _crash()]) == 1


def test_a_crash_among_real_grades_still_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _run_burst(monkeypatch, [_verdict("incorrect", "counterexample"), _crash()]) == 1


def test_ordinary_abstention_is_still_a_graded_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    timeout = {"status": "unable_to_verify", "reason": "not_proven", "method": "none"}
    assert _run_burst(monkeypatch, [_verdict("incorrect", "counterexample"), timeout]) == 0


def test_internal_error_label_is_unexpected_and_not_graded() -> None:
    results = [(200, "unable_to_verify:internal_error", 5.0), (200, "incorrect", 5.0)]
    _, unexpected = summarize(results)
    assert unexpected == 1 and graded(results) == 1
