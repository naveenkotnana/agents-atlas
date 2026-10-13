"""Atlas Enterprise Configuration Management using Pydantic Settings."""
import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "Atlas Enterprise Decision Intelligence"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "atlas-secret-key-default-replace-in-production"

    # Ollama LLM & Embedding Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3.2"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT_SECONDS: int = 60
    EMBEDDING_DIMENSION: int = 768

    # Database Settings (PostgreSQL + pgvector or local fallback)
    DATABASE_URL: str = "sqlite+aiosqlite:///./atlas_local.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5

    # Hybrid Search Settings
    TOP_K_RETRIEVAL: int = 10
    TOP_K_RERANK: int = 4
    RRF_K_CONSTANT: int = 60
    DENSE_WEIGHT: float = 0.60
    SPARSE_WEIGHT: float = 0.40
    RERANKER_TYPE: str = "cross_encoder"
    RERANK_MIN_SCORE: float = 0.30

    # LangGraph Decision Intelligence Settings
    MAX_REWRITE_CYCLES: int = 2
    HALLUCINATION_GUARD_THRESHOLD: float = 0.70
    DECISION_CONFIDENCE_THRESHOLD: float = 0.70

    # RAGAS Continuous Evaluation Settings
    RAGAS_EVAL_ENABLED: bool = True
    RAGAS_SAMPLE_RATE: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
