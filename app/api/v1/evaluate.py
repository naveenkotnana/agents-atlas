"""RAGAS Automated Evaluation Endpoints for Quality Benchmarking."""
from fastapi import APIRouter
from app.models.schema import EvaluationRequest, RAGASScoreResponse
from app.services.ragas_evaluator import ragas_evaluator

router = APIRouter(prefix="/evaluate", tags=["Continuous Evaluation (RAGAS)"])


@router.post("", response_model=RAGASScoreResponse)
async def evaluate_ragas_pipeline(payload: EvaluationRequest):
    """
    Evaluates RAG and decision quality using standard RAGAS metrics:
    - Faithfulness (ungrounded hallucination detection)
    - Answer Relevance (intent & topic alignment)
    - Context Precision (retrieval ranking quality)
    - Context Recall (ground truth coverage)
    """
    results = ragas_evaluator.evaluate(
        query=payload.query,
        answer=payload.answer,
        contexts=payload.contexts,
        ground_truth=payload.ground_truth
    )

    return RAGASScoreResponse(
        faithfulness=results["faithfulness"],
        answer_relevance=results["answer_relevance"],
        context_precision=results["context_precision"],
        context_recall=results["context_recall"],
        overall_score=results["overall_score"],
        verdict=results["verdict"]
    )
