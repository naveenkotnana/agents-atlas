# Atlas — Enterprise AI Knowledge & Decision Intelligence Platform
## Production Architecture, System Design & Operational Blueprint

### 1. Executive Overview
**Atlas** is an Enterprise Knowledge & Decision Intelligence Platform built with a modern Python AI stack. It bridges dense semantic understanding and sparse keyword precision, coordinates multi-step reasoning via **LangGraph**, guards against hallucinations with continuous scoring, and integrates automated evaluation with **RAGAS**.

```
                +-----------------------------------------+
                |     Enterprise Client / Dashboard UI    |
                +-----------------------------------------+
                                     |
                                     v
                +-----------------------------------------+
                |    FastAPI Production Gateway (Async)   |
                +-----------------------------------------+
                                     |
                                     v
                +-----------------------------------------+
                |    LangGraph Decision State Machine     |
                |  - Query Router & Analyzer              |
                |  - Adaptive Query Rewriter              |
                |  - Relevance & Factuality Graders       |
                |  - Synthesis & Confidence Scorer        |
                +-----------------------------------------+
                        /                   \
                       v                     v
+-------------------------------+  +-------------------------------+
|  Hybrid Retrieval (Dense+BM25)|  | Ollama Local Model Server     |
|  - PostgreSQL + pgvector HNSW |  | - Llama 3.2 / Qwen 2.5        |
|  - BM25 Inverted Index        |  | - Nomic-Embed-Text / BGE      |
|  - Reciprocal Rank Fusion(RRF)|  | - Cross-Encoder Reranker      |
+-------------------------------+  +-------------------------------+
                               |
                               v
                +-----------------------------------------+
                |    Continuous Observability & RAGAS     |
                |  - Faithfulness, Relevance, Precision   |
                |  - Automated Audit Traces               |
                +-----------------------------------------+
```

---

### 2. Core Pillars & Architecture

#### Pillar 1: Hybrid Retrieval Engine (BM25 + Dense + RRF)
- **Dense Vector Search**: Maps concepts and semantic similarities in 768-d space using cosine distance.
- **Sparse BM25 Search**: Captures precise keyword matches, acronyms, product numbers, and regulatory codes that dense vectors often blur.
- **Reciprocal Rank Fusion (RRF)**:
  `RRF_Score(doc) = (DENSE_WEIGHT / (60 + rank_dense)) + (SPARSE_WEIGHT / (60 + rank_bm25))`
  Eliminates distribution mismatch between cosine similarity and unbounded BM25 scores.

#### Pillar 2: Cross-Encoder Reranking
- Top 15-25 documents from hybrid retrieval are passed through a cross-encoder scoring stage.
- Cross-attention between `(Query, Document)` pairs achieves deep semantic calibration.
- Filters out low-confidence context chunks (threshold: `>= 0.35`).

#### Pillar 3: Adaptive Multi-Agent Reasoning via LangGraph
- **Graph State**: Contains `query`, `original_query`, `documents`, `reranked_docs`, `rewrite_count`, `decision`, `citations`, `confidence`.
- **Conditional Loops**: If retrieved documents fail the relevance grader, the query is rewritten and re-searched up to `MAX_REWRITE_CYCLES`.
- **Hallucination Guard**: Cross-verifies synthesized claims against citation chunks before final emission.

#### Pillar 4: Continuous Evaluation with RAGAS
- Every decision trace can be benchmarked against 4 key metrics:
  1. **Faithfulness**: Are claims supported by retrieved context?
  2. **Answer Relevance**: Does the answer directly address the original query?
  3. **Context Precision**: Did the retrieval put the best chunks at the top?
  4. **Context Recall**: Was all relevant context included in the retrieved set?

---

### 3. Production Deployment Guide
1. **Docker Compose**:
   ```bash
   docker compose up -d
   ```
2. **Access Atlas API & Interactive UI**:
   - Web Dashboard: `http://localhost:8000`
   - Swagger / OpenAPI: `http://localhost:8000/docs`
   - Health Probe: `http://localhost:8000/api/v1/health`
