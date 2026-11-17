"""Map a Grafana alert rule object to a standardized view."""

from __future__ import annotations

from typing import Any

from src.adapter.errors import MappingError
from src.standard.models import StandardField


class StandardRule:
    """A normalized view of an alert rule focused on standard fields."""

    def __init__(self, uid: str, title: str, labels: dict[str, str], annotations: dict[str, str]):
        self.uid = uid
        self.title = title
        self.labels = labels
        self.annotations = annotations


def map_rule_to_standard(raw_rule: dict[str, Any]) -> StandardRule:
    """Extract uid, title, labels, and annotations from a Grafana rule object."""
    uid = raw_rule.get("uid")
    if not uid:
        raise MappingError("RULE_UID_MISSING", "Rule object is missing 'uid'")

    title = raw_rule.get("title") or ""

    labels = _stringify_dict(raw_rule.get("labels", {}))
    annotations = _stringify_dict(raw_rule.get("annotations", {}))

    return StandardRule(
        uid=uid,
        title=title,
        labels=labels,
        annotations=annotations,
    )


def resolve_field_value(
    rule: StandardRule,
    field: StandardField,
) -> str | None:
    """Return the raw observed value for a standard field, or None if absent."""
    if field.location == "label":
        if field.name == "Appchi-$operator":
            return _find_appchi_operator_label(rule.labels)
        if field.name == "Send-Alert":
            return rule.labels.get("Send-Alert")
        if field.name == "component":
            return rule.labels.get("component") or rule.labels.get("object")
        return _get_case_insensitive(rule.labels, field.name)

    if field.location == "annotation":
        return rule.annotations.get(field.name)

    return None


def _get_case_insensitive(mapping: dict[str, str], key: str) -> str | None:
    """Look up a key case-insensitively, preferring an exact match."""
    if key in mapping:
        return mapping[key]
    key_lower = key.lower()
    for k, v in mapping.items():
        if k.lower() == key_lower:
            return v
    return None


def _stringify_dict(values: dict[str, Any]) -> dict[str, str]:
    """Coerce all label/annotation values to strings."""
    return {str(k): str(v) for k, v in values.items()}


def _find_appchi_operator_label(labels: dict[str, str]) -> str | None:
    """Find a label that starts with 'Appchi - ' and return it."""
    for key in labels:
        if key.startswith("Appchi - "):
            return key
    return None
