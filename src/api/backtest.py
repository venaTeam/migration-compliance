"""Backtest endpoint for alert rule historical replay."""

from __future__ import annotations

import time

from fastapi import APIRouter, Header

from src.backtest.engine import run_backtest
from src.backtest.models import BacktestRequest, BacktestResponse
from src.config import settings
from src.grafana.errors import GrafanaAPIError, GrafanaAuthError
from src.grafana.eval_client import GrafanaEvalClient

router = APIRouter()


@router.post("/backtest")
async def backtest(
    request: BacktestRequest,
    x_grafana_url: str = Header(..., alias="X-Grafana-Url"),
    x_grafana_username: str = Header(..., alias="X-Grafana-Username"),
    x_grafana_password: str = Header(..., alias="X-Grafana-Password"),
) -> BacktestResponse:
    """Evaluate how many times a rule would have fired over a recent window."""
    end_unix = int(time.time())
    start_unix = end_unix - (request.window_hours * 3600)

    eval_client = GrafanaEvalClient(
        base_url=x_grafana_url,
        username=x_grafana_username,
        password=x_grafana_password,
        verify=not settings.grafana_insecure_tls,
    )

    try:
        series_data = await eval_client.evaluate_query(
            request.rule_query,
            start_unix,
            end_unix,
        )
    except GrafanaAuthError:
        raise
    except GrafanaAPIError:
        raise

    return await run_backtest(request, series_data)
