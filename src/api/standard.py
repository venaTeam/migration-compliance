"""Standard schema endpoint."""

from fastapi import APIRouter

from src.standard.loader import load_standard_schema

router = APIRouter()


@router.get("/standard/schema")
def get_standard_schema() -> dict[str, object]:
    return load_standard_schema()
