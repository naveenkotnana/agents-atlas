"""Unit & Integration Tests for LangGraph Decision Intelligence State Machine."""
import pytest
from app.graph.state import AtlasGraphState
from app.graph.workflow import decision_graph


@pytest.mark.asyncio
async def test_langgraph_decision_pipeline():
    sample_chunks = [
        {
            "id": "chunk-101",
            "document_id": "doc-1",
            "document_title": "Atlas Enterprise Architecture",
            "content": (
                "Atlas Enterprise AI Platform guarantees 99.95% uptime SLA. "
                "P95 latency targets are under 1,500ms for hybrid retrieval and under 2,800ms for decision synthesis."
            ),
            "embedding": [0.05] * 768,
            "metadata": {"dept": "Engineering"}
        }
    ]

    initial_state: AtlasGraphState = {
        "query": "What is the P95 latency SLA target for Atlas decision synthesis?",
        "original_query": "What is the P95 latency SLA target for Atlas decision synthesis?",
        "rewritten_queries": [],
        "rewrite_count": 0,
        "intent": "general",
        "retrieved_documents": [],
        "reranked_documents": [],
        "documents_graded_relevant": False,
        "decision": "",
        "confidence_score": 0.0,
        "hallucination_guard_passed": False,
        "citations": [],
        "reasoning_steps": [],
        "trace_id": "test-trace-123",
        "all_corpus_chunks": sample_chunks
    }

    final_state = await decision_graph.run(initial_state)

    # Assertions on state transitions
    assert final_state["decision"] != ""
    assert len(final_state["citations"]) > 0
    assert final_state["confidence_score"] > 0.0
    assert len(final_state["reasoning_steps"]) >= 4

    # Verify citation fields
    citation = final_state["citations"][0]
    assert citation["chunk_id"] == "chunk-101"
    assert "Atlas Enterprise Architecture" in citation["document_title"]
