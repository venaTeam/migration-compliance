"""Per-field compliance evaluation engine."""

from __future__ import annotations

from typing import Any

from src.adapter.mapper import StandardRule, resolve_field_value
from src.evaluator import reason_codes as rc
from src.standard.models import (
    StandardField,
    get_standard_schema_model,
)


def evaluate_rule(
    rule: StandardRule,
    valid_notification_policies: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate a rule against the standard and return an EvaluateResponse-shaped dict."""
    schema = get_standard_schema_model()
    field_verdicts: list[dict[str, Any]] = []
    any_non_compliant = False

    for field in schema.fields:
        verdict = _evaluate_field(rule, field, valid_notification_policies or [])
        if verdict["status"] == "NON_COMPLIANT":
            any_non_compliant = True
        field_verdicts.append(verdict)

    return {
        "rule_uid": rule.uid,
        "rule_title": rule.title,
        "standard_version": schema.version,
        "overall_status": "NON_COMPLIANT" if any_non_compliant else "COMPLIANT",
        "fields": field_verdicts,
    }


def _evaluate_field(
    rule: StandardRule,
    field: StandardField,
    valid_policies: list[str],
) -> dict[str, Any]:
    """Evaluate a single standard field and return a FieldVerdict-shaped dict."""
    observed = resolve_field_value(rule, field)

    # Handle missing values
    if observed is None or observed == "":
        if field.required:
            return _verdict(
                field,
                observed,
                "NON_COMPLIANT",
                rc.MISSING_REQUIRED_FIELD,
                f"Required {field.location} '{field.name}' is missing.",
            )
        if field.default_value is not None:
            return _verdict(
                field,
                observed,
                "COMPLIANT",
                "DEFAULT_APPLIED",
                f"Optional {field.location} '{field.name}' is missing; "
                f"default '{field.default_value}' will be used.",
                default_value=field.default_value,
            )
        # Optional, no default -> compliant (e.g. application omitted)
        return _verdict(
            field,
            observed,
            "COMPLIANT",
            "OPTIONAL_ABSENT",
            f"Optional {field.location} '{field.name}' is absent and has no default.",
        )

    # Exact value constraint (e.g. Send Alert = true)
    if field.constraints.exact_value is not None:
        if observed != field.constraints.exact_value:
            return _verdict(
                field,
                observed,
                "NON_COMPLIANT",
                rc.INVALID_EXACT_VALUE,
                f"{field.location} '{field.name}' must be exactly "
                f"'{field.constraints.exact_value}', got '{observed}'.",
                expected_value=field.constraints.exact_value,
            )
        return _verdict(field, observed, "COMPLIANT", "VALUE_MATCHES", "")

    # Notification policy prefix / match (Appchi-$operator)
    if field.name == "Appchi-$operator":
        return _evaluate_appchi_operator(rule, field, observed, valid_policies)

    # Length constraints
    length = len(observed)
    if field.constraints.min_length is not None and length < field.constraints.min_length:
        return _verdict(
            field,
            observed,
            "NON_COMPLIANT",
            rc.VALUE_TOO_SHORT,
            f"{field.location} '{field.name}' is too short "
            f"({length} chars; minimum {field.constraints.min_length}).",
        )
    if field.constraints.max_length is not None and length > field.constraints.max_length:
        return _verdict(
            field,
            observed,
            "NON_COMPLIANT",
            rc.VALUE_TOO_LONG,
            f"{field.location} '{field.name}' is too long "
            f"({length} chars; maximum {field.constraints.max_length}).",
        )

    # Allowed values constraint
    if (
        field.constraints.allowed_values is not None
        and observed not in field.constraints.allowed_values
    ):
        return _verdict(
            field,
            observed,
            "NON_COMPLIANT",
            rc.VALUE_NOT_ALLOWED,
            f"{field.location} '{field.name}' value '{observed}' "
            f"is not one of {field.constraints.allowed_values}.",
            expected_value=", ".join(field.constraints.allowed_values),
        )

    return _verdict(field, observed, "COMPLIANT", "VALUE_VALID", "")


def _evaluate_appchi_operator(
    rule: StandardRule,
    field: StandardField,
    observed: str,
    valid_policies: list[str],
) -> dict[str, Any]:
    """Evaluate the Appchi-$operator label."""
    prefix = field.constraints.starts_with or "Appchi - "
    if not observed.startswith(prefix):
        return _verdict(
            field,
            observed,
            "NON_COMPLIANT",
            rc.VALUE_NOT_ALLOWED,
            f"{field.location} '{field.name}' must start with '{prefix}'.",
            expected_value=prefix,
        )

    # The operator label itself must carry the value "true" (see AlertsNewSchema).
    label_value = rule.labels.get(observed)
    if label_value != "true":
        return _verdict(
            field,
            observed,
            "NON_COMPLIANT",
            rc.OPERATOR_LABEL_VALUE_NOT_TRUE,
            f"Label '{observed}' must have the value 'true' (got "
            f"{'nothing' if label_value is None else repr(label_value)}).",
            expected_value="true",
        )

    if observed not in valid_policies:
        return _verdict(
            field,
            observed,
            "NON_COMPLIANT",
            rc.LABEL_DOES_NOT_MATCH_NOTIFICATION_POLICY,
            f"{field.location} '{field.name}' does not match any Grafana "
            f"notification policy starting with '{prefix}'.",
        )

    return _verdict(field, observed, "COMPLIANT", "VALUE_VALID", "")


def _verdict(
    field: StandardField,
    observed: str | None,
    status: str,
    reason_code: str,
    message: str,
    *,
    expected_value: str | None = None,
    default_value: str | None = None,
) -> dict[str, Any]:
    return {
        "name": field.name,
        "location": field.location,
        "status": status,
        "observed_value": observed,
        "expected_value": expected_value,
        "default_value": default_value if default_value is not None else field.default_value,
        "reason_code": reason_code,
        "message": message,
    }
