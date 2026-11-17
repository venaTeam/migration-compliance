"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.backtest import router as backtest_router
from src.api.errors import register_error_handlers
from src.api.evaluate import router as evaluate_router
from src.api.health import router as health_router
from src.api.policies import router as policies_router
from src.api.standard import router as standard_router
from src.config import settings

app = FastAPI(
    title="Alert Standard Compliance Engine",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(standard_router, prefix="/api/v1")
app.include_router(policies_router, prefix="/api/v1")
app.include_router(evaluate_router, prefix="/api/v1")
app.include_router(backtest_router, prefix="/api/v1")


def get_app() -> FastAPI:
    """Application factory used by Gunicorn/Uvicorn."""
    return app
