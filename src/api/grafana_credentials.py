"""Grafana credentials sent by callers: a service-account token or username + password."""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Header
from fastapi.exceptions import RequestValidationError

MISSING_CREDENTIAL_MSG = "Field required unless X-Grafana-Token is set"


@dataclass(frozen=True)
class GrafanaCredentials:
    url: str
    username: str | None = None
    password: str | None = field(default=None, repr=False)
    token: str | None = field(default=None, repr=False)


def grafana_credentials(
    x_grafana_url: str = Header(..., alias="X-Grafana-Url"),
    x_grafana_username: str | None = Header(None, alias="X-Grafana-Username"),
    x_grafana_password: str | None = Header(None, alias="X-Grafana-Password"),
    x_grafana_token: str | None = Header(None, alias="X-Grafana-Token"),
) -> GrafanaCredentials:
    """Use the token when present, otherwise require username and password."""
    if x_grafana_token:
        return GrafanaCredentials(url=x_grafana_url, token=x_grafana_token)
    require_basic_auth(
        "header",
        {"X-Grafana-Username": x_grafana_username, "X-Grafana-Password": x_grafana_password},
    )
    return GrafanaCredentials(
        url=x_grafana_url,
        username=x_grafana_username,
        password=x_grafana_password,
    )


def require_basic_auth(location: str, fields: dict[str, str | None]) -> None:
    """Raise a 422 shaped like FastAPI's own for each missing field."""
    errors = [
        # input is left empty so a submitted password is never echoed back.
        {"type": "missing", "loc": (location, name), "msg": MISSING_CREDENTIAL_MSG, "input": None}
        for name, value in fields.items()
        if value is None
    ]
    if errors:
        raise RequestValidationError(errors)
