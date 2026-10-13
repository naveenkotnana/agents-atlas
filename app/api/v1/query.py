"""Decision Intelligence Endpoint executing the LangGraph Adaptive Workflow."""
import time
import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.db_models import DecisionTrace, RagasEvaluationLog
from app.models.schema import (
    DecisionQueryRequest,
    DecisionQueryResponse,
    CitationItem,
    ReasoningStepItem,
)
from app.graph.state import AtlasGraphState
from app.graph.workflow import decision_graph
from app.services.ingestion import ingestion_service
from app.services.ragas_evaluator import ragas_evaluator
from app.core.logging import logger

router = APIRouter(prefix="/query", tags=["Decision Intelligence (LangGraph)"])


@router.post("", response_model=DecisionQueryResponse)
async def execute_decision_query(
    payload: DecisionQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Executes an enterprise decision query across the full LangGraph state machine:
    1. Query Decomposition & Intent Analyzer
    2. Hybrid Retrieval (BM25 + pgvector Dense + RRF)
    3. Cross-Encoder Reranking
    4. Document Relevance Grader (Adaptive Self-Correction Loop)
    5. Ollama LLM Decision Synthesis
    6. Hallucination & Factuality Guard
    7. Continuous RAGAS Quality Audit (Optional)
    """
    start_time = time.time()
    trace_id = str(uuid.uuid4())

    # 1. Fetch chunks from storage
    all_chunks = await ingestion_service.get_all_chunks(db)
    if not all_chunks:
        raise HTTPException(
            status_code=400,
            detail="Knowledge base is empty. Please ingest enterprise documents first."
        )

    # 2. Build initial state
    initial_state: AtlasGraphState = {
        "query": payload.query,
        "original_query": payload.query,
        "rewritten_queries": [],
        "rewrite_count": 0,
        "intent": "general",
        "retrieved_documents": [],
        "reranked_documents": [],
        "documents_graded_relevant": False,
        "decision": "",
        "confidence_score": 0.0,
        "hallucination_guard_passed": True,
        "citations": [],
        "reasoning_steps": [],
        "trace_id": trace_id,
        "all_corpus_chunks": all_chunks
    }

    # 3. Execute LangGraph State Machine
    final_state = await decision_graph.run(initial_state)

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    # 4. Optional RAGAS Evaluation
    ragas_scores = None
    if payload.evaluate_with_ragas:
        context_snippets = [c.get("snippet", "") for c in final_state.get("citations", [])]
        ragas_scores = ragas_evaluator.evaluate(
            query=payload.query,
            answer=final_state.get("decision", ""),
            contexts=context_snippets
        )

    # 5. Persist Decision Trace to DB for auditability
    try:
        chunk_ids = [c.get("chunk_id") for c in final_state.get("citations", [])]
        trace_record = DecisionTrace(
            id=trace_id,
            query_text=payload.query,
            transformed_query=final_state.get("query"),
            decision_output=final_state.get("decision", ""),
            confidence_score=final_state.get("confidence_score", 0.0),
            hallucination_guard_passed=1 if final_state.get("hallucination_guard_passed") else 0,
            retrieved_chunk_ids=chunk_ids,
            citations=final_state.get("citations", []),
            reasoning_steps=final_state.get("reasoning_steps", []),
            execution_time_ms=elapsed_ms
        )
        db.add(trace_record)

        if ragas_scores:
            eval_record = RagasEvaluationLog(
                trace_id=trace_id,
                faithfulness_score=ragas_scores["faithfulness"],
                answer_relevance_score=ragas_scores["answer_relevance"],
                context_precision_score=ragas_scores["context_precision"],
                context_recall_score=ragas_scores["context_recall"],
                overall_ragas_score=ragas_scores["overall_score"],
                evaluation_metadata={"verdict": ragas_scores["verdict"]}
            )
            db.add(eval_record)

        await db.commit()
    except Exception as e:
        logger.warning(f"Could not save decision audit trace: {e}")

    # 6. Format Response
    citations_model = [CitationItem(**c) for c in final_state.get("citations", [])]
    reasoning_model = [
        ReasoningStepItem(
            node_name=r.get("node_name", "Node"),
            action=r.get("action", ""),
            observation=r.get("observation", ""),
        )
        for r in final_state.get("reasoning_steps", [])
    ]

    return DecisionQueryResponse(
        trace_id=trace_id,
        query=payload.query,
        rewritten_queries=final_state.get("rewritten_queries", []),
        decision=final_state.get("decision", ""),
        confidence_score=final_state.get("confidence_score", 0.0),
        hallucination_guard_passed=final_state.get("hallucination_guard_passed", True),
        citations=citations_model,
        reasoning_steps=reasoning_model,
        execution_time_ms=elapsed_ms,
        ragas_evaluation=ragas_scores
    )
