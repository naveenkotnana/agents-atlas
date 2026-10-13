"""API v1 Central Router Aggregator."""
from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.search import router as search_router
from app.api.v1.query import router as query_router
from app.api.v1.evaluate import router as evaluate_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(ingest_router)
api_router.include_router(search_router)
api_router.include_router(query_router)
api_router.include_router(evaluate_router)
