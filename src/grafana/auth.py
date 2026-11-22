"""Auth helpers for Grafana API calls."""

from collections.abc import Generator
from typing import Literal

import httpx

AuthType = Literal["basic"]


def basic_auth_header(username: str, password: str) -> str:
    """Build a Basic Auth header value."""
    import base64

    credentials = f"{username}:{password}".encode()
    return f"Basic {base64.b64encode(credentials).decode('utf-8')}"


class BearerAuth(httpx.Auth):
    """Send a Grafana service-account token as a Bearer header."""

    def __init__(self, token: str):
        self._token = token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


def grafana_auth(
    username: str | None,
    password: str | None,
    token: str | None = None,
) -> httpx.Auth | tuple[str, str]:
    """Bearer auth when a token is given, otherwise basic auth."""
    if token:
        return BearerAuth(token)
    if username is None or password is None:
        raise ValueError("Grafana username and password are required without a token")
    return (username, password)
