from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Iterable


def percentile(values: Iterable[float], percentile_value: float) -> float | None:
    """Return a linearly interpolated percentile using rank (n - 1) * p."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    if not 0 <= percentile_value <= 100:
        raise ValueError("percentile_value must be between 0 and 100")
    rank = (len(ordered) - 1) * (percentile_value / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def summarize_samples(rows: Iterable[dict], duration_key: str = "duration_ms") -> dict:
    materialized = list(rows)
    durations = [float(row[duration_key]) for row in materialized if row.get(duration_key) is not None]
    success_count = sum(1 for row in materialized if row.get("success") is True)
    failure_count = len(materialized) - success_count
    summary = {
        "sample_count": len(materialized),
        "mean_ms": statistics.fmean(durations) if durations else None,
        "median_ms": statistics.median(durations) if durations else None,
        "p95_ms": percentile(durations, 95),
        "p99_ms": percentile(durations, 99),
        "min_ms": min(durations) if durations else None,
        "max_ms": max(durations) if durations else None,
        "standard_deviation_ms": statistics.pstdev(durations) if len(durations) > 1 else 0.0 if durations else None,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": success_count / len(materialized) if materialized else 0.0,
        "failure_rate": failure_count / len(materialized) if materialized else 0.0,
    }
    return summary


def grouped_summary(rows: Iterable[dict], keys: tuple[str, ...], duration_key: str = "duration_ms") -> dict:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key) for key in keys)].append(row)
    return {
        "|".join(str(value) for value in group_key): summarize_samples(group_rows, duration_key)
        for group_key, group_rows in sorted(groups.items(), key=lambda item: tuple(str(value) for value in item[0]))
    }
