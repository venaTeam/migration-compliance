"""Grafana read client."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from src.grafana.auth import grafana_auth
from src.grafana.errors import GrafanaAuthError, RuleNotFoundError


class GrafanaClient:
    """Read-only Grafana client for alert rules and notification policies."""

    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 10.0,
        verify: bool = True,
        token: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify = verify
        self._auth = grafana_auth(username, password, token)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            auth=self._auth,
            timeout=self.timeout,
            headers={"Accept": "application/json"},
            verify=self.verify,
        )

    async def get_rule(self, rule_url_or_uid: str) -> dict[str, Any]:
        """Fetch an alert rule by URL or UID."""
        uid = _extract_uid(rule_url_or_uid)
        async with self._client() as client:
            response = await client.get(f"/api/v1/provisioning/alert-rules/{uid}")
            if response.status_code == 404:
                raise RuleNotFoundError(f"Rule '{uid}' not found or not accessible")
            if response.status_code == 401:
                raise GrafanaAuthError("Invalid Grafana credentials")
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data

    async def list_notification_policies(self, prefix: str) -> list[str]:
        """List notification policy names matching the given prefix.

        Tries the provisioning endpoint first, then falls back to the tree endpoint.
        """
        policies: list[str] = []
        async with self._client() as client:
            response = await client.get("/api/v1/provisioning/policies")
            if response.status_code == 401:
                raise GrafanaAuthError("Invalid Grafana credentials")
            response.raise_for_status()
            data = response.json()
            policies.extend(_collect_policy_names(data, prefix))
        return policies


def _extract_uid(rule_url_or_uid: str) -> str:
    """Extract a rule UID from a Grafana URL or return the UID as-is."""
    if "/" not in rule_url_or_uid and "\\" not in rule_url_or_uid:
        return rule_url_or_uid.strip()

    parsed = urlparse(rule_url_or_uid)
    path = parsed.path.rstrip("/")

    patterns = [
        r"/alerting/grafana/(?P<uid>[^/]+)/(?:view|edit)",
        r"/alerting/(?P<uid>[^/]+)/(?:view|edit)",
    ]
    reserved_segments = {"view", "edit", "new", "grafana", "alerting"}

    for pattern in patterns:
        match = re.search(pattern, path)
        if match:
            uid = match.group("uid")
            if uid and uid not in reserved_segments:
                return uid

    # Last path segment fallback
    segments = [segment for segment in path.split("/") if segment]
    if segments and segments[-1] not in reserved_segments:
        return segments[-1]

    raise ValueError(f"Could not extract rule UID from '{rule_url_or_uid}'")


def _collect_policy_names(data: dict[str, Any] | list[Any], prefix: str) -> list[str]:
    """Recursively collect policy names/contact points starting with prefix."""
    names: list[str] = []
    if isinstance(data, dict):
        for key in ("receiver", "contactPoint", "name"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(prefix):
                names.append(value)
        for child in data.get("routes", []):
            names.extend(_collect_policy_names(child, prefix))
    elif isinstance(data, list):
        for item in data:
            names.extend(_collect_policy_names(item, prefix))
    return names
