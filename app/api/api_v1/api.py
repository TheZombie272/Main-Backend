from fastapi import APIRouter
from app.api.api_v1.endpoints import health, metrics, scripts

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
# Scripts endpoints (e.g. trigger download pipeline)
api_router.include_router(scripts.router, prefix="/scripts", tags=["scripts"])
