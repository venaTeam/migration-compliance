"""Pydantic models for the alert standard and evaluation API."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class FieldConstraints(BaseModel):
    min_length: int | None = None
    max_length: int | None = None
    allowed_values: list[str] | None = None
    exact_value: str | None = None
    starts_with: str | None = None


class StandardField(BaseModel):
    name: str
    location: Literal["label", "annotation"]
    required: bool
    explanation: str = ""
    constraints: FieldConstraints
    default_value: str | None = None


class StandardSchema(BaseModel):
    version: str
    fields: list[StandardField]


class EvaluateRequest(BaseModel):
    rule_url: str = Field(..., description="Grafana alert rule URL or UID")
    grafana_url: str = Field(..., description="Grafana base URL")
    grafana_username: str | None = Field(None, description="Not needed when X-Grafana-Token is set")
    grafana_password: str | None = Field(None, description="Not needed when X-Grafana-Token is set")


class FieldVerdict(BaseModel):
    name: str
    location: Literal["label", "annotation"]
    status: Literal["COMPLIANT", "NON_COMPLIANT"]
    observed_value: str | None = None
    expected_value: str | None = None
    default_value: str | None = None
    reason_code: str
    message: str = ""


class EvaluateResponse(BaseModel):
    rule_uid: str
    rule_title: str
    folder_uid: str | None = None
    standard_version: str
    overall_status: Literal["COMPLIANT", "NON_COMPLIANT"]
    fields: list[FieldVerdict]


def _schema_path() -> Path:
    return Path(__file__).parent / "schema.json"


def load_standard_schema() -> dict[str, object]:
    """Load and return the standard schema as a dict (for the API)."""
    schema_path = _schema_path()
    return StandardSchema.model_validate_json(
        schema_path.read_text(encoding="utf-8")
    ).model_dump()


def get_standard_schema_model() -> StandardSchema:
    """Return the validated StandardSchema model."""
    schema_path = _schema_path()
    return StandardSchema.model_validate_json(schema_path.read_text(encoding="utf-8"))
