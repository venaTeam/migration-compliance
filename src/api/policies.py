"""Notification policies endpoint."""

from fastapi import APIRouter, Header, Query

from src.config import settings
from src.grafana.client import GrafanaClient

router = APIRouter()


@router.get("/notification-policies")
async def get_notification_policies(
    prefix: str = Query(..., description="Filter policies whose names start with this prefix"),
    x_grafana_url: str = Header(..., alias="X-Grafana-Url"),
    x_grafana_username: str = Header(..., alias="X-Grafana-Username"),
    x_grafana_password: str = Header(..., alias="X-Grafana-Password"),
) -> dict[str, list[str]]:
    client = GrafanaClient(
        base_url=x_grafana_url,
        username=x_grafana_username,
        password=x_grafana_password,
        verify=not settings.grafana_insecure_tls,
    )
    policies = await client.list_notification_policies(prefix=prefix)
    return {"policies": policies}
