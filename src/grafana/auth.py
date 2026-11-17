"""Auth helpers for Grafana API calls."""

from typing import Literal

AuthType = Literal["basic"]


def basic_auth_header(username: str, password: str) -> str:
    """Build a Basic Auth header value."""
    import base64

    credentials = f"{username}:{password}".encode()
    return f"Basic {base64.b64encode(credentials).decode('utf-8')}"
