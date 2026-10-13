"""Conditional Routing Edges for LangGraph Decision Intelligence State Machine."""
from typing import Literal
from app.graph.state import AtlasGraphState


def should_generate_or_rewrite(state: AtlasGraphState) -> Literal["synthesize_decision", "rewrite_query"]:
    """
    Conditional edge: Evaluates document grading verdict.
    Routes to synthesis if evidence is sufficient, or to query rewrite loop if insufficient.
    """
    if state.get("documents_graded_relevant", False):
        return "synthesize_decision"
    return "rewrite_query"
