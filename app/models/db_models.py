"""SQLAlchemy Database Models for Atlas Platform."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False, default="text")
    source_uri = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    embedding = Column(JSON, nullable=True)  # Stores vector embedding list [float]
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


class DecisionTrace(Base):
    __tablename__ = "decision_traces"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    query_text = Column(Text, nullable=False)
    transformed_query = Column(Text, nullable=True)
    decision_output = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.0)
    hallucination_guard_passed = Column(Integer, default=1)
    retrieved_chunk_ids = Column(JSON, default=list)
    citations = Column(JSON, default=list)
    reasoning_steps = Column(JSON, default=list)
    execution_time_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    evaluations = relationship("RagasEvaluationLog", back_populates="trace", cascade="all, delete-orphan")


class RagasEvaluationLog(Base):
    __tablename__ = "ragas_evaluation_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    trace_id = Column(String(36), ForeignKey("decision_traces.id", ondelete="CASCADE"), nullable=True)
    faithfulness_score = Column(Float, default=0.0)
    answer_relevance_score = Column(Float, default=0.0)
    context_precision_score = Column(Float, default=0.0)
    context_recall_score = Column(Float, default=0.0)
    overall_ragas_score = Column(Float, default=0.0)
    evaluation_metadata = Column(JSON, default=dict)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    trace = relationship("DecisionTrace", back_populates="evaluations")
