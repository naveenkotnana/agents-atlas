"""Pydantic V2 Data Models & Serialization Schemas."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Document & Chunk Ingestion Schemas
# -------------------------------------------------------------
class DocumentIngestRequest(BaseModel):
    title: str = Field(..., description="Title of the document")
    content: str = Field(..., description="Full text content of the document")
    source_type: str = Field("text", description="Format: pdf, markdown, text, json")
    source_uri: Optional[str] = Field(None, description="Source URI or file path")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")


class ChunkItem(BaseModel):
    id: str
    chunk_index: int
    content: str
    token_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    id: str
    title: str
    source_type: str
    source_uri: Optional[str]
    chunk_count: int
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------
# Hybrid Search & Reranking Schemas
# -------------------------------------------------------------
class HybridSearchRequest(BaseModel):
    query: str = Field(..., description="User search query")
    top_k: int = Field(10, description="Top-K results to retrieve in initial hybrid stage")
    rerank_top_k: int = Field(4, description="Top-K candidates after Cross-Encoder reranking")
    apply_reranker: bool = Field(True, description="Whether to apply the Cross-Encoder stage")
    dense_weight: float = Field(0.6, description="Weight for Dense Vector search in RRF")
    sparse_weight: float = Field(0.4, description="Weight for Sparse BM25 search in RRF")


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    dense_rank: Optional[int] = None
    sparse_rank: Optional[int] = None
    rrf_score: float
    rerank_score: Optional[float] = None
    is_reranked: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HybridSearchResponse(BaseModel):
    query: str
    total_candidates: int
    results: List[SearchResultItem]
    execution_time_ms: float


# -------------------------------------------------------------
# LangGraph Decision Intelligence Schemas
# -------------------------------------------------------------
class CitationItem(BaseModel):
    chunk_id: str
    document_title: str
    snippet: str
    relevance_score: float


class ReasoningStepItem(BaseModel):
    node_name: str
    action: str
    observation: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DecisionQueryRequest(BaseModel):
    query: str = Field(..., description="Enterprise decision question or complex inquiry")
    session_id: Optional[str] = Field(None, description="Conversation session identifier")
    max_rewrite_cycles: int = Field(2, description="Maximum self-correction rewrite iterations")
    evaluate_with_ragas: bool = Field(False, description="Trigger on-the-fly RAGAS evaluation")


class DecisionQueryResponse(BaseModel):
    trace_id: str
    query: str
    rewritten_queries: List[str] = Field(default_factory=list)
    decision: str
    confidence_score: float
    hallucination_guard_passed: bool
    citations: List[CitationItem]
    reasoning_steps: List[ReasoningStepItem]
    execution_time_ms: float
    ragas_evaluation: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------
# RAGAS Quality Evaluation Schemas
# -------------------------------------------------------------
class EvaluationRequest(BaseModel):
    query: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None


class RAGASScoreResponse(BaseModel):
    faithfulness: float = Field(..., description="Metric: Factually grounded in context (0.0-1.0)")
    answer_relevance: float = Field(..., description="Metric: Relevance to original question (0.0-1.0)")
    context_precision: float = Field(..., description="Metric: Ranking precision of retrieved context")
    context_recall: float = Field(..., description="Metric: Coverage of ground truth context")
    overall_score: float = Field(..., description="Harmonic / weighted composite RAGAS score")
    verdict: str = Field(..., description="Quality assessment verdict")
