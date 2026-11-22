"""Rule evaluation endpoint."""

from fastapi import APIRouter, Depends

from src.adapter.mapper import map_rule_to_standard
from src.api.grafana_credentials import GrafanaCredentials, grafana_credentials, require_basic_auth
from src.config import settings
from src.evaluator.engine import evaluate_rule
from src.grafana.client import GrafanaClient
from src.standard.models import EvaluateRequest, EvaluateResponse

router = APIRouter()


@router.post("/evaluate")
async def evaluate(
    request: EvaluateRequest,
    credentials: GrafanaCredentials = Depends(grafana_credentials),
) -> EvaluateResponse:
    if credentials.token is None:
        # Without a token the body must still carry the credentials, as before.
        require_basic_auth(
            "body",
            {
                "grafana_username": request.grafana_username,
                "grafana_password": request.grafana_password,
            },
        )
    client = GrafanaClient(
        base_url=credentials.url,
        username=credentials.username,
        password=credentials.password,
        token=credentials.token,
        verify=not settings.grafana_insecure_tls,
    )
    rule = await client.get_rule(request.rule_url)
    policies = await client.list_notification_policies(prefix="Appchi - ")
    standard_rule = map_rule_to_standard(rule)
    result = evaluate_rule(standard_rule, valid_notification_policies=policies)
    return EvaluateResponse.model_validate(result)
