"""Integration Tests for FastAPI Endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "operational"
        assert "database" in data


@pytest.mark.asyncio
async def test_ragas_evaluate_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "query": "What are SOC2 encryption standards?",
            "answer": "SOC2 mandates AES-256 for data at rest and TLS 1.3 for data in transit.",
            "contexts": [
                "All enterprise data at rest must be encrypted using AES-256. All data in transit requires TLS 1.3 encryption."
            ]
        }
        res = await client.post("/api/v1/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "faithfulness" in data
        assert "answer_relevance" in data
        assert "overall_score" in data
