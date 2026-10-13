"""Hybrid Search Service: Dense Vector (Cosine) + Sparse BM25 + Reciprocal Rank Fusion (RRF)."""
import re
import math
import numpy as np
from typing import List, Dict, Any, Tuple
from app.config import settings
from app.core.logging import logger
from app.services.ollama_client import ollama_client


class HybridRetriever:
    def __init__(self):
        self.k_constant = settings.RRF_K_CONSTANT
        self.dense_weight = settings.DENSE_WEIGHT
        self.sparse_weight = settings.SPARSE_WEIGHT

    def tokenize(self, text: str) -> List[str]:
        """Simple, fast tokenization for sparse BM25 scoring."""
        text = text.lower()
        tokens = re.findall(r"\b[a-z0-9_\-\.]{2,}\b", text)
        # Minimal stopword filter
        stopwords = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "to", "in", "of", "for", "with", "as"}
        return [t for t in tokens if t not in stopwords]

    def compute_bm25_scores(self, query: str, documents: List[Dict[str, Any]]) -> List[float]:
        """Compute BM25 Okapi scores for all candidate chunks."""
        query_tokens = self.tokenize(query)
        if not query_tokens or not documents:
            return [0.0] * len(documents)

        # Tokenize corpus
        corpus_tokens = [self.tokenize(doc["content"]) for doc in documents]
        n_docs = len(documents)
        avg_dl = sum(len(doc_t) for doc_t in corpus_tokens) / max(n_docs, 1)

        # Calculate Document Frequencies (DF)
        df: Dict[str, int] = {}
        for doc_t in corpus_tokens:
            unique_terms = set(doc_t)
            for term in unique_terms:
                df[term] = df.get(term, 0) + 1

        # BM25 Hyperparameters
        k1 = 1.5
        b = 0.75

        scores = []
        for doc_t in corpus_tokens:
            doc_len = len(doc_t)
            score = 0.0
            term_freqs: Dict[str, int] = {}
            for t in doc_t:
                term_freqs[t] = term_freqs.get(t, 0) + 1

            for q_term in query_tokens:
                if q_term in term_freqs:
                    freq = term_freqs[q_term]
                    doc_freq = df.get(q_term, 0)
                    # Standard Robertson-Jones IDF
                    idf = math.log((n_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
                    # BM25 Term Weight
                    numerator = freq * (k1 + 1.0)
                    denominator = freq + k1 * (1.0 - b + b * (doc_len / max(avg_dl, 1e-6)))
                    score += idf * (numerator / denominator)
            scores.append(score)

        return scores

    def compute_cosine_similarity(self, query_vec: List[float], doc_vec: List[float]) -> float:
        """Compute Cosine Similarity between query and chunk embedding vectors."""
        if not query_vec or not doc_vec:
            return 0.0
        q = np.array(query_vec, dtype=np.float32)
        d = np.array(doc_vec, dtype=np.float32)
        norm_q = np.linalg.norm(q)
        norm_d = np.linalg.norm(d)
        if norm_q == 0.0 or norm_d == 0.0:
            return 0.0
        return float(np.dot(q, d) / (norm_q * norm_d))

    async def search(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 10,
        dense_weight: float = None,
        sparse_weight: float = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval:
        1. Dense Vector Scoring
        2. Sparse BM25 Scoring
        3. Reciprocal Rank Fusion (RRF) Ranking
        """
        if not chunks:
            return []

        w_dense = dense_weight if dense_weight is not None else self.dense_weight
        w_sparse = sparse_weight if sparse_weight is not None else self.sparse_weight

        # 1. Query vector for Dense search
        query_embedding = await ollama_client.get_embeddings(query)

        # 2. Compute Dense Similarity scores
        dense_scores = []
        for chunk in chunks:
            c_emb = chunk.get("embedding") or []
            dense_scores.append(self.compute_cosine_similarity(query_embedding, c_emb))

        # 3. Compute Sparse BM25 scores
        bm25_scores = self.compute_bm25_scores(query, chunks)

        # 4. Rank candidates for each strategy
        # Dense ranking (highest score -> rank 1)
        dense_ranked_indices = np.argsort(dense_scores)[::-1]
        dense_rank_map = {idx: rank + 1 for rank, idx in enumerate(dense_ranked_indices)}

        # Sparse ranking (highest score -> rank 1)
        sparse_ranked_indices = np.argsort(bm25_scores)[::-1]
        sparse_rank_map = {idx: rank + 1 for rank, idx in enumerate(sparse_ranked_indices)}

        # 5. Calculate Reciprocal Rank Fusion (RRF)
        fused_results = []
        for idx, chunk in enumerate(chunks):
            r_dense = dense_rank_map[idx]
            r_sparse = sparse_rank_map[idx]

            rrf_score = (
                w_dense * (1.0 / (self.k_constant + r_dense)) +
                w_sparse * (1.0 / (self.k_constant + r_sparse))
            )

            item = dict(chunk)
            item["dense_score"] = float(dense_scores[idx])
            item["dense_rank"] = r_dense
            item["bm25_score"] = float(bm25_scores[idx])
            item["sparse_rank"] = r_sparse
            item["rrf_score"] = float(rrf_score)
            fused_results.append(item)

        # Sort by RRF score descending
        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused_results[:top_k]


hybrid_retriever = HybridRetriever()
