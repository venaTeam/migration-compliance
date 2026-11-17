"""Backtest engine: count threshold breaches from evaluated time series."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.backtest.models import BacktestRequest, BacktestResponse, LabelSetResult


async def run_backtest(
    request: BacktestRequest,
    series_data: list[dict[str, Any]],
) -> BacktestResponse:
    """Run a backtest over pre-evaluated time series data."""
    per_label_set: list[LabelSetResult] = []
    total_breaches = 0

    for series in series_data:
        labels = _stringify_labels(series.get("labels", {}))
        points = series.get("points", [])
        firing_periods = _detect_firing_periods(
            points,
            request.threshold,
            request.condition,
            request.for_duration_seconds,
        )
        breach_count = len(firing_periods)
        total_breaches += breach_count
        per_label_set.append(
            LabelSetResult(
                labels=labels,
                breach_count=breach_count,
                firing_periods=firing_periods,
            )
        )

    message = _build_message(total_breaches, len(per_label_set))

    return BacktestResponse(
        rule_query=request.rule_query,
        threshold=request.threshold,
        condition=request.condition,
        window_hours=request.window_hours,
        total_breaches=total_breaches,
        per_label_set=per_label_set,
        message=message,
    )


def _detect_firing_periods(
    points: list[dict[str, Any]],
    threshold: float,
    condition: str,
    for_duration_seconds: int,
) -> list[tuple[str, str]]:
    """Detect firing periods from a time series, honoring for_duration_seconds."""
    if not points:
        return []

    comparator = _comparator(condition)
    sorted_points = sorted(points, key=lambda p: int(p["timestamp"]))

    periods: list[tuple[str, str]] = []
    current_start: int | None = None
    previous_ts: int | None = None

    for point in sorted_points:
        ts = int(point["timestamp"])
        value = float(point["value"])
        is_breach = comparator(value, threshold)

        if is_breach:
            if current_start is None:
                current_start = ts
        elif (
            current_start is not None
            and previous_ts is not None
            and previous_ts - current_start >= for_duration_seconds
        ):
            periods.append((_format_ts(current_start), _format_ts(previous_ts)))
            current_start = None
        else:
            current_start = None

        previous_ts = ts

    # Close an open period at the end.
    if (
        current_start is not None
        and previous_ts is not None
        and previous_ts - current_start >= for_duration_seconds
    ):
        periods.append((_format_ts(current_start), _format_ts(previous_ts)))

    return periods


def _comparator(condition: str) -> Any:
    """Return a comparator function for the given condition string."""
    operators = {
        "gt": lambda v, t: v > t,
        "gte": lambda v, t: v >= t,
        "lt": lambda v, t: v < t,
        "lte": lambda v, t: v <= t,
        "eq": lambda v, t: v == t,
        "neq": lambda v, t: v != t,
    }
    return operators.get(condition, operators["gt"])


def _format_ts(timestamp: int) -> str:
    """Format a Unix timestamp as ISO 8601."""
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _stringify_labels(labels: dict[str, Any]) -> dict[str, str]:
    """Coerce label values to strings."""
    return {str(k): str(v) for k, v in labels.items()}


def _build_message(total_breaches: int, label_set_count: int) -> str:
    if total_breaches == 0:
        return "The rule would not have fired during this window."
    if label_set_count == 1:
        return f"The rule would have fired {total_breaches} time(s) during this window."
    return (
        f"The rule would have fired {total_breaches} time(s) across "
        f"{label_set_count} label set(s) during this window."
    )
