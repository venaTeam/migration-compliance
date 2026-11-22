"""Grafana credentials on the API endpoints, and folder_uid on /evaluate."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import respx

from src.main import app

pytestmark = pytest.mark.asyncio

GRAFANA = "https://grafana.test"
TOKEN = "glsa_test_token"
PASSWORD = "s3cret-pass"
BEARER = f"Bearer {TOKEN}"
BASIC = "Basic " + base64.b64encode(f"alice:{PASSWORD}".encode()).decode()

TOKEN_HEADERS = {"X-Grafana-Url": GRAFANA, "X-Grafana-Token": TOKEN}
BASIC_HEADERS = {
    "X-Grafana-Url": GRAFANA,
    "X-Grafana-Username": "alice",
    "X-Grafana-Password": PASSWORD,
}

RULE = {
    "uid": "rule-1",
    "title": "CPU high",
    "folderUID": "folder-1",
    "labels": {},
    "annotations": {},
}
EVALUATE_BODY = {"rule_url": f"{GRAFANA}/alerting/grafana/rule-1/view", "grafana_url": GRAFANA}
BASIC_EVALUATE_BODY = {**EVALUATE_BODY, "grafana_username": "alice", "grafana_password": PASSWORD}

# (method, path, request kwargs with a token, request kwargs with basic auth)
ENDPOINTS: dict[str, tuple[str, str, dict[str, Any], dict[str, Any]]] = {
    "evaluate": (
        "POST",
        "/api/v1/evaluate",
        {"json": EVALUATE_BODY},
        {"json": BASIC_EVALUATE_BODY},
    ),
    "policies": (
        "GET",
        "/api/v1/notification-policies",
        {"params": {"prefix": "Appchi - "}},
        {"params": {"prefix": "Appchi - "}},
    ),
    "backtest": (
        "POST",
        "/api/v1/backtest",
        {"json": {"rule_query": "up", "threshold": 1}},
        {"json": {"rule_query": "up", "threshold": 1}},
    ),
}


@pytest.fixture
def grafana() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=GRAFANA, assert_all_called=False) as router:
        router.get("/api/v1/provisioning/alert-rules/rule-1", name="rule").respond(json=RULE)
        router.get("/api/v1/provisioning/policies").respond(json={"receiver": "Appchi - ops"})
        router.post("/api/v1/eval").respond(json={"results": {"A": {"frames": []}}})
        yield router


async def call(method: str, path: str, headers: dict[str, str], **kwargs: Any) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://compliance") as client:
        return await client.request(method, path, headers=headers, **kwargs)


def sent_auth(router: respx.MockRouter) -> list[str | None]:
    return [c.request.headers.get("Authorization") for c in router.calls]


async def test_evaluate_returns_folder_uid(grafana: respx.MockRouter) -> None:
    response = await call("POST", "/api/v1/evaluate", TOKEN_HEADERS, json=EVALUATE_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["rule_uid"] == "rule-1"
    assert body["folder_uid"] == "folder-1"


async def test_evaluate_folder_uid_is_null_when_rule_has_none(grafana: respx.MockRouter) -> None:
    grafana["rule"].respond(json={k: v for k, v in RULE.items() if k != "folderUID"})

    response = await call("POST", "/api/v1/evaluate", BASIC_HEADERS, json=BASIC_EVALUATE_BODY)

    assert response.status_code == 200
    assert response.json()["folder_uid"] is None


@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_token_sends_bearer_header(grafana: respx.MockRouter, endpoint: str) -> None:
    method, path, token_kwargs, _ = ENDPOINTS[endpoint]

    response = await call(method, path, TOKEN_HEADERS, **token_kwargs)

    assert response.status_code == 200, response.text
    assert grafana.calls.call_count > 0
    assert sent_auth(grafana) == [BEARER] * grafana.calls.call_count


async def test_token_takes_precedence_over_basic_auth(grafana: respx.MockRouter) -> None:
    headers = {**BASIC_HEADERS, "X-Grafana-Token": TOKEN}

    response = await call("POST", "/api/v1/evaluate", headers, json=BASIC_EVALUATE_BODY)

    assert response.status_code == 200
    assert sent_auth(grafana) == [BEARER] * grafana.calls.call_count


@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_basic_auth_unchanged(grafana: respx.MockRouter, endpoint: str) -> None:
    method, path, _, basic_kwargs = ENDPOINTS[endpoint]

    response = await call(method, path, BASIC_HEADERS, **basic_kwargs)

    assert response.status_code == 200, response.text
    assert grafana.calls.call_count > 0
    assert sent_auth(grafana) == [BASIC] * grafana.calls.call_count


@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_missing_credentials_rejected(grafana: respx.MockRouter, endpoint: str) -> None:
    method, path, _, basic_kwargs = ENDPOINTS[endpoint]

    response = await call(method, path, {"X-Grafana-Url": GRAFANA}, **basic_kwargs)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert [tuple(e["loc"]) for e in errors] == [
        ("header", "X-Grafana-Username"),
        ("header", "X-Grafana-Password"),
    ]
    assert all("X-Grafana-Token" in e["msg"] for e in errors)
    assert not grafana.calls


async def test_evaluate_without_token_still_requires_body_credentials(
    grafana: respx.MockRouter,
) -> None:
    response = await call("POST", "/api/v1/evaluate", BASIC_HEADERS, json=EVALUATE_BODY)

    assert response.status_code == 422
    locs = [tuple(e["loc"]) for e in response.json()["detail"]]
    assert locs == [("body", "grafana_username"), ("body", "grafana_password")]
    assert not grafana.calls


async def test_rejection_does_not_echo_password(grafana: respx.MockRouter) -> None:
    headers = {"X-Grafana-Url": GRAFANA, "X-Grafana-Password": PASSWORD}
    body = {**EVALUATE_BODY, "grafana_password": PASSWORD}

    header_response = await call("POST", "/api/v1/evaluate", headers, json=body)
    body_response = await call(
        "POST", "/api/v1/evaluate", {**BASIC_HEADERS, "X-Grafana-Password": "x"}, json=body
    )

    for response in (header_response, body_response):
        assert response.status_code == 422
        assert PASSWORD not in response.text
