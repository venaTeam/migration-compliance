"""Global API error handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.adapter.errors import MappingError
from src.grafana.errors import GrafanaAPIError, GrafanaAuthError, RuleNotFoundError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(GrafanaAuthError)
    async def auth_error_handler(_request: Request, exc: GrafanaAuthError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "message": str(exc)},
        )

    @app.exception_handler(RuleNotFoundError)
    async def not_found_handler(_request: Request, exc: RuleNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": "Not Found", "message": str(exc)},
        )

    @app.exception_handler(GrafanaAPIError)
    async def grafana_api_handler(_request: Request, exc: GrafanaAPIError) -> JSONResponse:
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
