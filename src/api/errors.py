"""Global API error handlers."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.adapter.errors import MappingError
from src.grafana.errors import GrafanaAPIError, GrafanaAuthError, RuleNotFoundError


SECRET_KEYS = ("password", "token")


def _is_secret(key: object) -> bool:
    return isinstance(key, str) and any(word in key.lower() for word in SECRET_KEYS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: "[redacted]" if _is_secret(k) else _redact(v) for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def redact_validation_errors(errors: Any) -> list[dict[str, Any]]:
    """Validation errors without submitted passwords or tokens in `input`."""
    redacted = []
    for error in errors:
        error = dict(error)
        loc = error.get("loc") or ()
        if loc and _is_secret(loc[-1]):
            error.pop("input", None)
        elif "input" in error:
            error["input"] = _redact(error["input"])
        redacted.append(error)
    return redacted


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        detail = jsonable_encoder(redact_validation_errors(exc.errors()))
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.exception_handler(GrafanaAuthError)
    async def auth_error_handler(
        _request: Request, exc: GrafanaAuthError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "message": str(exc)},
        )

    @app.exception_handler(RuleNotFoundError)
    async def not_found_handler(
        _request: Request, exc: RuleNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": "Not Found", "message": str(exc)},
        )

    @app.exception_handler(GrafanaAPIError)
    async def grafana_api_handler(
        _request: Request, exc: GrafanaAPIError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"error": "Grafana API Error", "message": str(exc)},
        )

    @app.exception_handler(MappingError)
    async def mapping_handler(_request: Request, exc: MappingError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Mapping Error",
                "message": exc.message,
                "reason_code": exc.reason_code,
            },
        )
