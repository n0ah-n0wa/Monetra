"""Latency aggregation for load test results."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True, slots=True)
class RequestResult:
    scenario: str
    latency_ms: float
    status_code: int
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400


@dataclass(frozen=True, slots=True)
class ScenarioStats:
    scenario: str
    samples: int
    successes: int
    failures: int
    min_ms: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float

    @property
    def error_rate(self) -> float:
        if self.samples == 0:
            return 0.0
        return self.failures / self.samples


def percentile(sorted_values: list[float], pct: float) -> float:
    """Return the ``pct`` percentile (0-100) from a sorted list."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def summarize_scenario(scenario: str, results: list[RequestResult]) -> ScenarioStats:
    latencies = sorted(result.latency_ms for result in results)
    successes = sum(1 for result in results if result.success)
    failures = len(results) - successes
    return ScenarioStats(
        scenario=scenario,
        samples=len(results),
        successes=successes,
        failures=failures,
        min_ms=latencies[0] if latencies else 0.0,
        mean_ms=mean(latencies) if latencies else 0.0,
        p50_ms=percentile(latencies, 50),
        p95_ms=percentile(latencies, 95),
        p99_ms=percentile(latencies, 99),
        max_ms=latencies[-1] if latencies else 0.0,
    )


def format_stats_table(rows: list[ScenarioStats]) -> str:
    header = (
        f"{'Scenario':<24} {'OK':>5} {'Fail':>5} "
        f"{'p50':>8} {'p95':>8} {'p99':>8} {'max':>8}"
    )
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{row.scenario:<24} {row.successes:>5} {row.failures:>5} "
            f"{row.p50_ms:>7.1f}ms {row.p95_ms:>7.1f}ms "
            f"{row.p99_ms:>7.1f}ms {row.max_ms:>7.1f}ms",
        )
    return "\n".join(lines)
