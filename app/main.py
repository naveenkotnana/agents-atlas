"""Atlas Enterprise AI Knowledge & Decision Intelligence Platform
Main FastAPI Application Entrypoint.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func

from app.config import settings
from app.core.logging import setup_logging, logger
from app.core.database import init_db, AsyncSessionLocal
from app.models.db_models import Document
from app.services.ingestion import ingestion_service
from app.api.v1.router import api_router


SAMPLE_ENTERPRISE_DOCUMENTS = [
    {
        "title": "Atlas Enterprise AI Architecture & SLA Standards",
        "source_type": "markdown",
        "source_uri": "s3://enterprise-docs/atlas/architecture_sla_2026.md",
        "content": (
            "Atlas Enterprise AI Architecture and SLA Standards Specification:\n\n"
            "1. High-Availability & Service Level Agreements (SLA):\n"
            "Atlas guarantees 99.95% uptime for all Decision Intelligence endpoints across multi-zone deployments. "
            "P95 latency targets are strictly under 1,500ms for full hybrid search retrieval and Cross-Encoder reranking, "
            "and under 2,800ms for complete LangGraph multi-agent decision synthesis.\n\n"
            "2. Hybrid Retrieval Pipeline:\n"
            "The system deploys dual-indexing: dense vector embeddings are generated using nomic-embed-text (768 dimensions) "
            "indexed via PostgreSQL pgvector with HNSW indexing (m=16, ef_construction=64). "
            "Sparse retrieval is powered by BM25 with Okapi weighting, stemmed using Porter stemming. "
            "Results are merged via Reciprocal Rank Fusion (RRF) with smoothing parameter k=60, applying weights "
            "0.60 for dense vector and 0.40 for sparse BM25.\n\n"
            "3. Cross-Encoder Reranking:\n"
            "The top 15 candidate chunks from hybrid retrieval are reranked via a secondary Cross-Encoder model. "
            "Chunks scoring below the calibrated threshold of 0.35 are discarded from prompt context."
        ),
        "metadata": {"department": "Engineering", "confidentiality": "Internal", "version": "2.4"}
    },
    {
        "title": "Global Cloud Infrastructure & Disaster Recovery RTO/RPO Policy",
        "source_type": "text",
        "source_uri": "s3://enterprise-docs/compliance/disaster_recovery_policy.txt",
        "content": (
            "Enterprise Global Cloud Infrastructure and Disaster Recovery Guidelines:\n\n"
            "1. Recovery Objectives:\n"
            "For Tier-1 mission-critical systems including Atlas Decision Core and PostgreSQL pgvector databases, "
            "the Recovery Point Objective (RPO) is 5 minutes or less, achieved through continuous asynchronous replication. "
            "The Recovery Time Objective (RTO) is 15 minutes or less with automated DNS failover across secondary regions.\n\n"
            "2. Data Redundancy and Backups:\n"
            "Point-in-time recovery (PITR) is enabled for 35 days. Daily encrypted immutable snapshots are replicated "
            "to isolated, air-gapped storage buckets. Restoration drills are conducted quarterly under audit supervision."
        ),
        "metadata": {"department": "DevOps & Infrastructure", "confidentiality": "Restricted", "tier": "1"}
    },
    {
        "title": "SOC2 Type II Compliance & Data Encryption Controls",
        "source_type": "text",
        "source_uri": "s3://enterprise-docs/security/soc2_type_ii_controls.pdf",
        "content": (
            "SOC2 Type II Security, Confidentiality and Encryption Controls:\n\n"
            "1. Cryptographic Standards:\n"
            "All enterprise data at rest must be encrypted using AES-256 with AWS KMS or HashiCorp Vault managed keys. "
            "All data in transit requires TLS 1.3 encryption. Unencrypted HTTP traffic is rejected at ingress.\n\n"
            "2. Role-Based Access Control (RBAC) & LLM Privacy:\n"
            "Tenant data ingested into Atlas is strictly isolated using row-level security (RLS). "
            "Prompts and embeddings generated through Ollama and local LLM runners are never stored by third-party providers "
            "or utilized for external foundation model retraining."
        ),
        "metadata": {"department": "Security & GRC", "confidentiality": "Confidential", "soc2_control": "CC6.1"}
    },
    {
        "title": "Executive Product Strategy & 2026 AI Roadmap",
        "source_type": "markdown",
        "source_uri": "s3://enterprise-docs/strategy/roadmap_2026.md",
        "content": (
            "Executive Product Strategy & 2026 AI Roadmap:\n\n"
            "1. Core Objective: Shift from passive conversational RAG to proactive Decision Intelligence.\n"
            "Atlas empowers leadership to query multi-modal enterprise data, execute automated trade-off analyses, "
            "and verify evidentiary grounding before committing executive resources.\n\n"
            "2. Continuous RAGAS Benchmarking:\n"
            "All deployment gates require continuous RAGAS evaluation scores: Faithfulness >= 0.88, Answer Relevance >= 0.85, "
            "and Context Precision >= 0.80. Any PR failing these benchmarks will fail CI/CD build validation."
        ),
        "metadata": {"department": "Executive Leadership", "confidentiality": "Internal", "target_year": 2026}
    }
]


async def seed_knowledge_base():
    """Seeds sample documents if the knowledge base is empty on boot."""
    async with AsyncSessionLocal() as session:
        count_res = await session.execute(select(func.count(Document.id)))
        count = count_res.scalar() or 0
        if count == 0:
            logger.info("Initializing knowledge base with sample enterprise documents...")
            for doc_data in SAMPLE_ENTERPRISE_DOCUMENTS:
                await ingestion_service.ingest_document(
                    db=session,
                    title=doc_data["title"],
                    content=doc_data["content"],
                    source_type=doc_data["source_type"],
                    source_uri=doc_data["source_uri"],
                    metadata=doc_data["metadata"]
                )
            logger.info("Enterprise knowledge base pre-seeded successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI application lifespan: startup and shutdown logic."""
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    await init_db()
    await seed_knowledge_base()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Atlas is an Enterprise AI Knowledge & Decision Intelligence Platform powered by "
        "Python, Ollama, LangGraph, Hybrid Search (Dense + BM25 + RRF), Cross-Encoder Reranking, "
        "and RAGAS Automated Quality Evaluation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Static files for Enterprise UI Dashboard
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
