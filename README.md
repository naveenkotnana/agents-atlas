# Atlas — Enterprise AI Knowledge & Decision Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent%20Workflow-FF6F00.svg)](https://github.com/langchain-ai/langgraph)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM%20Serving-000000.svg)](https://ollama.ai)
[![RAGAS](https://img.shields.io/badge/RAGAS-Continuous%20Evaluation-8A2BE2.svg)](https://github.com/explodinggradients/ragas)
[![Docker](https://img.shields.io/badge/Docker-Production%20Compose-2496ED.svg)](https://www.docker.com/)

---

## 1. System Overview

**Atlas** is an Enterprise Knowledge & Decision Intelligence Platform engineered for high-accuracy reasoning, verifiable source attribution, and resilient knowledge retrieval across complex enterprise data silos.

Unlike naive RAG systems that rely solely on flat cosine similarity, Atlas implements an **Adaptive Multi-Agent Decision Engine** powered by:
- **FastAPI (Async Core)**: High-throughput async RESTful gateway with streaming, lifespans, and telemetry.
- **PostgreSQL 16 + pgvector**: Dense embeddings (768-d HNSW indexing with $m=16, ef\_construction=64$).
- **Sparse BM25 Search**: Full-text inverted index with Porter stemming and Robertson-Jones IDF.
- **Reciprocal Rank Fusion (RRF)**: Rank-based fusion balancing semantic context and lexical keyword precision.
- **Cross-Encoder Reranking**: Second-stage deep attention scoring eliminating false-positive semantic matches.
- **LangGraph Multi-Agent Engine**: Adaptive state machine with query decomposition, self-correction rewriting loops, and factuality guards.
- **Ollama Local LLM Serving**: Privacy-preserving, on-premises LLM orchestration (`llama3.2`, `qwen2.5`, `nomic-embed-text`).
- **RAGAS Automated Evaluation**: Automated auditing for **Faithfulness**, **Answer Relevance**, **Context Precision**, and **Context Recall**.
- **Enterprise Web Dashboard**: Interactive UI featuring real-time LangGraph step animations, hybrid search rank explorer, and citation verification.

---

## 2. Production Architecture Diagram

```mermaid
flowchart TB
    subgraph ClientLayer ["1. Client & Integration Layer"]
        UI["Atlas Web Dashboard (Enterprise Glassmorphism UI)"]
        SDK["Enterprise REST / Python SDK Clients"]
        BI["BI & Analytics Systems / Webhooks"]
    end

    subgraph APIGateway ["2. API Gateway & Ingress Layer (FastAPI)"]
        FastAPI["FastAPI Async Core"]
        AuthMiddleware["JWT / API Key & RBAC Security"]
        Telemetry["Structured Logging & OpenTelemetry"]
    end

    subgraph LangGraphEngine ["3. Decision Intelligence Engine (LangGraph State Machine)"]
        State["AtlasGraphState (Query, Context, Confidence, Reasoning)"]
        RouterNode["1. Intent & Query Decomposer Node"]
        HybridRetrieveNode["2. Hybrid Retrieval Node (BM25 + Dense)"]
        RerankNode["3. Cross-Encoder Reranker Node"]
        DocGraderNode["4. Hallucination & Relevance Grader Node"]
        QueryRewriter["5. Adaptive Query Rewriter Node (Self-Correction Loop)"]
        DecisionNode["6. Decision Synthesis & Reasoning Node (Ollama LLM)"]
        FactChecker["7. Factuality & Hallucination Guard Node"]
    end

    subgraph RetrievalLayer ["4. Hybrid Search & Storage Layer (PostgreSQL + pgvector)"]
        PG[(PostgreSQL 16 Enterprise)]
        PGVector["pgvector Extension (HNSW Indexing)"]
        PGBM25["BM25 Inverted Lexical Index"]
        RRF["Reciprocal Rank Fusion (RRF)"]
    end

    subgraph LLMExecution ["5. Inference & Model Serving (Ollama / Local LLMs)"]
        OllamaLLM["Ollama Core (Llama 3.2 / Qwen 2.5 / DeepSeek-R1)"]
        OllamaEmbed["Embedding Engine (nomic-embed-text / bge-large-en)"]
        CrossEncoder["Cross-Encoder Reranking Pipeline"]
    end

    subgraph EvaluationLayer ["6. Observability & Continuous Evaluation (RAGAS)"]
        RAGASWorker["RAGAS Automated Evaluation Engine"]
        Metrics["Faithfulness | Answer Relevance | Context Precision | Context Recall"]
        AuditDB[(Audit & Decision Trace DB)]
    end

    UI --> FastAPI
    SDK --> FastAPI
    BI --> FastAPI
    FastAPI --> AuthMiddleware --> Telemetry --> LangGraphEngine

    RouterNode --> HybridRetrieveNode
    HybridRetrieveNode --> RetrievalLayer
    RetrievalLayer --> RerankNode
    RerankNode --> DocGraderNode
    DocGraderNode -- "Relevant" --> DecisionNode
    DocGraderNode -- "Irrelevant / Ambiguous" --> QueryRewriter --> HybridRetrieveNode
    DecisionNode --> FactChecker
    FactChecker --> State

    LangGraphEngine <--> LLMExecution
    LangGraphEngine --> AuditDB
    AuditDB --> RAGASWorker --> Metrics
```

---

## 3. Quick Start & Production Deployment

### Option A: Complete Docker Compose Deployment (Recommended for Production)

Ensure Docker & Docker Compose are installed:

```bash
# 1. Clone & enter repository
cd d:\AGENTS

# 2. Launch PostgreSQL (pgvector), Ollama, and Atlas API
docker compose up -d

# 3. Pull recommended models into Ollama container
docker exec -it atlas_ollama ollama pull llama3.2
docker exec -it atlas_ollama ollama pull nomic-embed-text
```

The services will be live at:
- **Web Dashboard**: `http://localhost:8000`
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`
- **Health Probe**: `http://localhost:8000/api/v1/health`

---

### Option B: Local Standalone Development

Atlas supports standalone development with automated SQLite fallback when PostgreSQL is not running:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the platform
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Comprehensive readiness probe (DB, Ollama, Vector Indices). |
| `POST` | `/api/v1/query` | Executes the LangGraph Multi-Agent Decision Intelligence workflow. |
| `POST` | `/api/v1/search` | Inspects Dense vs BM25 vs RRF vs Cross-Encoder rankings. |
| `POST` | `/api/v1/documents` | Ingests enterprise documents with recursive chunking & embeddings. |
| `GET` | `/api/v1/documents` | Lists all indexed documents and chunk statistics. |
| `DELETE`| `/api/v1/documents/{id}`| Deletes a document and cascade removes its vector chunks. |
| `POST` | `/api/v1/evaluate` | Runs the RAGAS Quality Assurance benchmark. |

---

### Example: Decision Intelligence Request

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are our SLA targets for decision latency and how does disaster recovery handle RTO?",
    "evaluate_with_ragas": true,
    "max_rewrite_cycles": 2
  }'
```

---

## 5. Continuous Evaluation with RAGAS

Atlas enforces continuous evaluation across four dimensions:
1. **Faithfulness**: Verifies that every assertion made by the LLM is substantiated by citations.
2. **Answer Relevance**: Ensures answers directly resolve the user's inquiry without drift.
3. **Context Precision**: Confirms that top-ranked chunks have higher evidentiary value than lower-ranked ones.
4. **Context Recall**: Verifies that no ground-truth requirements were missed during retrieval.

---

## 6. Running Tests

```bash
pytest -v
```
