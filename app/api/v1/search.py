"""Hybrid Search & Cross-Encoder Reranking Inspection Endpoints."""
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.schema import HybridSearchRequest, HybridSearchResponse, SearchResultItem
from app.services.ingestion import ingestion_service
from app.services.hybrid_retriever import hybrid_retriever
from app.services.reranker import reranker

router = APIRouter(prefix="/search", tags=["Hybrid Search & Reranking"])


@router.post("", response_model=HybridSearchResponse)
async def execute_hybrid_search(
    payload: HybridSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Executes and inspects:
    1. Dense Vector Search (Cosine similarity)
    2. Sparse Lexical Search (BM25 Okapi)
    3. Reciprocal Rank Fusion (RRF)
    4. Optional Cross-Encoder Reranking
    """
    start_time = time.time()
    
    # 1. Fetch chunks
    all_chunks = await ingestion_service.get_all_chunks(db)
    if not all_chunks:
        raise HTTPException(
            status_code=400,
            detail="Knowledge base is empty. Please ingest enterprise documents first."
        )

    # 2. Hybrid Retrieval
    candidates = await hybrid_retriever.search(
        query=payload.query,
        chunks=all_chunks,
        top_k=payload.top_k,
        dense_weight=payload.dense_weight,
        sparse_weight=payload.sparse_weight
    )

    # 3. Optional Cross-Encoder Reranking
    final_results = candidates
    if payload.apply_reranker and candidates:
        final_results = await reranker.rerank(
            query=payload.query,
            candidates=candidates,
            top_k=payload.rerank_top_k
        )

    # 4. Format response items
    items = []
    for r in final_results:
        items.append(SearchResultItem(
            chunk_id=r.get("chunk_id", r.get("id", "")),
            document_id=r.get("document_id", ""),
            document_title=r.get("document_title", "Document"),
            content=r.get("content", ""),
            dense_rank=r.get("dense_rank"),
            sparse_rank=r.get("sparse_rank"),
            rrf_score=round(r.get("rrf_score", 0.0), 5),
            rerank_score=r.get("rerank_score"),
            is_reranked=r.get("is_reranked", False),
            metadata=r.get("metadata", {})
        ))

    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return HybridSearchResponse(
        query=payload.query,
        total_candidates=len(all_chunks),
        results=items,
        execution_time_ms=elapsed_ms
    )
