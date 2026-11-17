"""Rule evaluation endpoint."""

from fastapi import APIRouter, Header

from src.adapter.mapper import map_rule_to_standard
from src.config import settings
from src.evaluator.engine import evaluate_rule
from src.grafana.client import GrafanaClient
from src.standard.models import EvaluateRequest, EvaluateResponse

router = APIRouter()


@router.post("/evaluate")
async def evaluate(
    request: EvaluateRequest,
    x_grafana_url: str = Header(..., alias="X-Grafana-Url"),
    x_grafana_username: str = Header(..., alias="X-Grafana-Username"),
    x_grafana_password: str = Header(..., alias="X-Grafana-Password"),
) -> EvaluateResponse:
    client = GrafanaClient(
        base_url=x_grafana_url,
        username=x_grafana_username,
        password=x_grafana_password,
        verify=not settings.grafana_insecure_tls,
    )
    rule = await client.get_rule(request.rule_url)
    policies = await client.list_notification_policies(prefix="Appchi - ")
    standard_rule = map_rule_to_standard(rule)
    result = evaluate_rule(standard_rule, valid_notification_policies=policies)
    return EvaluateResponse.model_validate(result)
