"""Atlas LangGraph State Schema."""
from typing import TypedDict, List, Dict, Any, Optional


class AtlasGraphState(TypedDict):
    query: str
    original_query: str
    rewritten_queries: List[str]
    rewrite_count: int
    intent: str
    retrieved_documents: List[Dict[str, Any]]
    reranked_documents: List[Dict[str, Any]]
    documents_graded_relevant: bool
    decision: str
    confidence_score: float
    hallucination_guard_passed: bool
    citations: List[Dict[str, Any]]
    reasoning_steps: List[Dict[str, Any]]
    trace_id: str
    all_corpus_chunks: List[Dict[str, Any]]
