"""Grafana expression evaluation client for backtesting."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from src.grafana.errors import GrafanaAPIError, GrafanaAuthError


class GrafanaEvalClient:
    """Client for Grafana's /api/v1/eval endpoint."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: float = 30.0,
        verify: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify = verify

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            auth=(self.username, self.password),
            timeout=self.timeout,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            verify=self.verify,
        )

    async def evaluate_query(
        self,
        query: str,
        start_unix: int,
        end_unix: int,
    ) -> list[dict[str, Any]]:
        """Evaluate a query over a time range via Grafana's expr endpoint.

        Falls back to the datasource proxy query endpoint if /api/v1/eval is unavailable.
        """
        async with self._client() as client:
            # Try the unified expression endpoint first.
            payload = {
                "queries": [
                    {
                        "refId": "A",
                        "queryType": "",
                        "relativeTimeRange": {"from": start_unix, "to": end_unix},
                        "datasourceUid": "__expr__",
                        "model": {
                            "type": "math",
                            "expression": query,
                            "refId": "A",
                        },
                    }
                ]
            }
            response = await client.post("/api/v1/eval", json=payload)
            if response.status_code == 401:
                raise GrafanaAuthError("Invalid Grafana credentials")
            if response.status_code == 404:
                # Fall back to a direct Prometheus-style range query via proxy.
                return await self._prometheus_range_query(client, query, start_unix, end_unix)
            response.raise_for_status()
            data = response.json()
            return _parse_eval_response(data)

    async def _prometheus_range_query(
        self,
        client: httpx.AsyncClient,
        query: str,
        start_unix: int,
        end_unix: int,
    ) -> list[dict[str, Any]]:
        """Fallback range query through the Prometheus datasource proxy."""
        step = _suggest_step(start_unix, end_unix)
        url = (
            f"/api/datasources/proxy/uid/prometheus/api/v1/query_range?"
            f"query={quote(query)}&start={start_unix}&end={end_unix}&step={step}"
        )
        response = await client.get(url)
        if response.status_code == 401:
            raise GrafanaAuthError("Invalid Grafana credentials")
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "success":
            raise GrafanaAPIError(f"Prometheus query failed: {data.get('error', 'unknown error')}")
        return _parse_prometheus_range_response(data.get("data", {}))


def _suggest_step(start_unix: int, end_unix: int) -> str:
    """Suggest a Prometheus step based on the time range."""
    duration = end_unix - start_unix
    if duration <= 3600:
        return "15s"
    if duration <= 86400:
        return "1m"
    return "5m"


def _parse_eval_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the /api/v1/eval response into a normalized list of time series."""
    results: list[dict[str, Any]] = []
    for frame in data.get("results", {}).get("A", {}).get("frames", []):
        schema = frame.get("schema", {})
        fields = frame.get("data", {}).get("values", [])
        labels = schema.get("labels") or schema.get("tags") or {}
        if len(fields) >= 2:
            timestamps = fields[0]
            values = fields[1]
            points = [
                {"timestamp": ts, "value": _to_float(v)}
                for ts, v in zip(timestamps, values, strict=False)
                if _to_float(v) is not None
            ]
            if points:
                results.append({"labels": labels, "points": points})
    return results


def _parse_prometheus_range_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Prometheus /api/v1/query_range response into normalized series."""
    results: list[dict[str, Any]] = []
    for series in data.get("result", []):
        labels = series.get("metric", {})
        points: list[dict[str, Any]] = []
        for ts, value in series.get("values", []):
            float_value = _to_float(value)
            if float_value is not None:
                points.append({"timestamp": int(ts), "value": float_value})
        if points:
            results.append({"labels": labels, "points": points})
    return results


def _to_float(value: Any) -> float | None:
    """Coerce a value to float, returning None on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
