"""A load run must distinguish database failure from expected verifier backpressure."""

from load.submit_burst import summarize


def test_br4_database_busy_is_not_expected_verifier_backpressure():
    report, unexpected = summarize([(503, "database_busy", 5000.0)] * 16)
    assert unexpected == 16, report
