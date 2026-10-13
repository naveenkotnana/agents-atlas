"""Unit & Integration Tests for Hybrid Search & Cross-Encoder Reranking."""
import pytest
from app.services.hybrid_retriever import hybrid_retriever
from app.services.reranker import reranker
from app.services.ragas_evaluator import ragas_evaluator


from app.services.ollama_client import ollama_client


@pytest.mark.asyncio
async def test_bm25_and_rrf_scoring():
    raw_chunks = [
        {
            "id": "c1",
            "document_title": "Architecture Doc",
            "content": "PostgreSQL with pgvector provides HNSW indexing for high speed vector queries."
        },
        {
            "id": "c2",
            "document_title": "Disaster Recovery",
            "content": "Disaster recovery policy specifies an RTO of 15 minutes and RPO of 5 minutes."
        },
        {
            "id": "c3",
            "document_title": "SOC2 Controls",
            "content": "SOC2 encryption mandates AES-256 at rest and TLS 1.3 in transit."
        }
    ]

    chunks = []
    for rc in raw_chunks:
        emb = await ollama_client.get_embeddings(rc["content"])
        chunks.append({**rc, "embedding": emb})

    # Search for Disaster Recovery
    results = await hybrid_retriever.search(
        query="What is the RPO for disaster recovery?",
        chunks=chunks,
        top_k=2
    )

    assert len(results) <= 2
    # Chunk c2 should rank highest due to both BM25 and semantic match
    top_chunk = results[0]
    assert top_chunk["id"] == "c2"
    assert "rrf_score" in top_chunk
    assert top_chunk["rrf_score"] > 0


@pytest.mark.asyncio
async def test_cross_encoder_reranking():
    candidates = [
        {"id": "1", "content": "The weather today in New York is cloudy.", "rrf_score": 0.02},
        {"id": "2", "content": "Atlas uses Cross-Encoder reranking for precision context filtering.", "rrf_score": 0.025}
    ]

    reranked = await reranker.rerank(
        query="Cross-Encoder precision filtering",
        candidates=candidates,
        top_k=2
    )

    assert len(reranked) == 2
    assert reranked[0]["id"] == "2"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]


def test_ragas_evaluation_metrics():
    query = "What is our database RPO?"
    answer = "The database RPO is strictly 5 minutes or less."
    contexts = [
        "For Tier-1 mission-critical systems, the Recovery Point Objective (RPO) is 5 minutes or less."
    ]

    scores = ragas_evaluator.evaluate(query, answer, contexts)
    assert scores["faithfulness"] >= 0.80
    assert scores["answer_relevance"] >= 0.65
    assert scores["overall_score"] > 0.60
    assert scores["verdict"] in ["Production Ready", "Acceptable Quality"]
