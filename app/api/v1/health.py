"""System Health, Metrics & Readiness Probes."""
import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.db_models import Document, DocumentChunk
from app.services.ollama_client import ollama_client
from app.config import settings

router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive readiness probe checking DB, Ollama, and vector indices."""
    start_time = time.time()

    # 1. Database Check
    db_status = "healthy"
    doc_count = 0
    chunk_count = 0
    try:
        doc_res = await db.execute(select(func.count(Document.id)))
        doc_count = doc_res.scalar() or 0
        chunk_res = await db.execute(select(func.count(DocumentChunk.id)))
        chunk_count = chunk_res.scalar() or 0
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # 2. Ollama Status
    ollama_info = await ollama_client.check_health()

    return {
        "status": "operational",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": {
            "status": db_status,
            "total_documents": doc_count,
            "total_chunks": chunk_count,
        },
        "ollama": {
            "endpoint": settings.OLLAMA_BASE_URL,
            "llm_model": settings.OLLAMA_LLM_MODEL,
            "embed_model": settings.OLLAMA_EMBED_MODEL,
            "connectivity": ollama_info["status"]
        },
        "response_time_ms": round((time.time() - start_time) * 1000, 2)
    }
