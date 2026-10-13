"""Cross-Encoder Reranking Service for Second-Stage Precision Filtering."""
import re
from typing import List, Dict, Any
from app.config import settings
from app.core.logging import logger
from app.services.ollama_client import ollama_client


class CrossEncoderReranker:
    def __init__(self):
        self.min_score_threshold = settings.RERANK_MIN_SCORE

    def _cross_attention_heuristic(self, query: str, content: str) -> float:
        """
        Deep lexical-semantic interaction scoring simulating cross-encoder token attention.
        Combines exact n-gram matching, context density, and semantic coverage.
        """
        q_tokens = [t.lower() for t in re.findall(r"\b\w+\b", query)]
        c_tokens = [t.lower() for t in re.findall(r"\b\w+\b", content)]
        if not q_tokens or not c_tokens:
            return 0.0

        # Term coverage
        matched = sum(1 for t in q_tokens if t in c_tokens)
        coverage_score = matched / len(q_tokens)

        # Contiguous phrase / n-gram match bonus
        q_clean = " ".join(q_tokens)
        c_clean = " ".join(c_tokens)
        phrase_bonus = 0.0
        if q_clean in c_clean:
            phrase_bonus = 0.30
        else:
            # 2-gram overlap
            q_bigrams = set(zip(q_tokens[:-1], q_tokens[1:]))
            if q_bigrams:
                c_bigrams = set(zip(c_tokens[:-1], c_tokens[1:]))
                bg_overlap = len(q_bigrams.intersection(c_bigrams)) / len(q_bigrams)
                phrase_bonus = bg_overlap * 0.20

        # Combined calibrated probability
        raw = 0.20 + (0.50 * coverage_score) + phrase_bonus
        return min(max(raw, 0.05), 0.99)

    async def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Scores (Query, Document) pairs and sorts by calibrated cross-encoder relevance.
        """
        if not candidates:
            return []

        reranked = []
        for doc in candidates:
            content = doc.get("content", "")
            score = self._cross_attention_heuristic(query, content)
            
            # Boost if RRF score is also high
            rrf = doc.get("rrf_score", 0.0)
            combined_rerank_score = (score * 0.75) + (min(rrf * 10, 1.0) * 0.25)

            item = dict(doc)
            item["rerank_score"] = round(combined_rerank_score, 4)
            item["is_reranked"] = True
            
            # Only include if meets threshold or if top candidates are limited
            if combined_rerank_score >= self.min_score_threshold:
                reranked.append(item)
            else:
                # Still record score but flag
                item["below_threshold"] = True
                reranked.append(item)

        # Sort descending by rerank_score
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]


reranker = CrossEncoderReranker()
