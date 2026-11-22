"""Notification policies endpoint."""

from fastapi import APIRouter, Depends, Query

from src.api.grafana_credentials import GrafanaCredentials, grafana_credentials
from src.config import settings
from src.grafana.client import GrafanaClient

router = APIRouter()


@router.get("/notification-policies")
async def get_notification_policies(
    prefix: str = Query(
        ..., description="Filter policies whose names start with this prefix"
    ),
    credentials: GrafanaCredentials = Depends(grafana_credentials),
) -> dict[str, list[str]]:
    client = GrafanaClient(
        base_url=credentials.url,
        username=credentials.username,
        password=credentials.password,
        token=credentials.token,
        verify=not settings.grafana_insecure_tls,
    )
    policies = await client.list_notification_policies(prefix=prefix)
    return {"policies": policies}
