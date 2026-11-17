"""Grafana client exceptions."""


class GrafanaError(Exception):
    """Base Grafana error."""


class GrafanaAuthError(GrafanaError):
    """Invalid or insufficient credentials."""


class GrafanaAPIError(GrafanaError):
    """Unexpected Grafana API error."""


class RuleNotFoundError(GrafanaError):
    """Rule not found or not accessible."""
