"""Tests for load-test statistics helpers."""

from loadtest.stats import RequestResult, percentile, summarize_scenario


def test_percentile_interpolates() -> None:
    values = [10.0, 20.0, 30.0, 40.0]
    assert percentile(values, 50) == 25.0
    assert percentile(values, 95) == 38.5


def test_summarize_scenario_counts_failures() -> None:
    results = [
        RequestResult("auth_login", 12.0, 200),
        RequestResult("auth_login", 18.0, 401, error="unauthorized"),
        RequestResult("auth_login", 15.0, 200),
    ]
    stats = summarize_scenario("auth_login", results)
    assert stats.samples == 3
    assert stats.successes == 2
    assert stats.failures == 1
    assert stats.p50_ms == 15.0
