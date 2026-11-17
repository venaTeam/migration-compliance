"""Pydantic models for the backtest API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    rule_query: str = Field(..., description="Prometheus-style query expression")
    threshold: float = Field(..., description="Threshold value to compare against")
    condition: Literal["gt", "gte", "lt", "lte", "eq", "neq"] = Field(
        default="gt",
        description="Comparison operator between query value and threshold",
    )
    for_duration_seconds: int = Field(
        default=0,
        description="Minimum consecutive breach duration before firing (Grafana 'for')",
    )
    window_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Historical window to evaluate, in hours",
    )


class LabelSetResult(BaseModel):
    labels: dict[str, str]
    breach_count: int
    firing_periods: list[tuple[str, str]] = Field(
        default_factory=list,
        description="List of (start, end) ISO timestamps for counted firing periods",
    )


class BacktestResponse(BaseModel):
    rule_query: str
    threshold: float
    condition: str
    window_hours: int
    total_breaches: int
    per_label_set: list[LabelSetResult]
    message: str = ""
