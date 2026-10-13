"""LangGraph Workflow Assembler & Runtime Engine for Atlas Platform."""
from typing import Dict, Any
from app.graph.state import AtlasGraphState
from app.graph.nodes import (
    node_analyze_query,
    node_hybrid_retrieve,
    node_rerank_candidates,
    node_grade_documents,
    node_rewrite_query,
    node_synthesize_decision,
    node_fact_check_guard,
)
from app.graph.edges import should_generate_or_rewrite
from app.core.logging import logger

# Attempt to import LangGraph StateGraph, or use native asynchronous state runner
try:
    from langgraph.graph import StateGraph, START, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    START = "__start__"
    END = "__end__"


class AtlasDecisionGraph:
    def __init__(self):
        self.app = None
        if LANGGRAPH_AVAILABLE:
            try:
                workflow = StateGraph(AtlasGraphState)

                # Add nodes
                workflow.add_node("analyze_query", node_analyze_query)
                workflow.add_node("hybrid_retrieve", node_hybrid_retrieve)
                workflow.add_node("rerank_candidates", node_rerank_candidates)
                workflow.add_node("grade_documents", node_grade_documents)
                workflow.add_node("rewrite_query", node_rewrite_query)
                workflow.add_node("synthesize_decision", node_synthesize_decision)
                workflow.add_node("fact_check_guard", node_fact_check_guard)

                # Set edges
                workflow.add_edge(START, "analyze_query")
                workflow.add_edge("analyze_query", "hybrid_retrieve")
                workflow.add_edge("hybrid_retrieve", "rerank_candidates")
                workflow.add_edge("rerank_candidates", "grade_documents")

                # Conditional branching
                workflow.add_conditional_edges(
                    "grade_documents",
                    should_generate_or_rewrite,
                    {
                        "synthesize_decision": "synthesize_decision",
                        "rewrite_query": "rewrite_query"
                    }
                )
                workflow.add_edge("rewrite_query", "hybrid_retrieve")
                workflow.add_edge("synthesize_decision", "fact_check_guard")
                workflow.add_edge("fact_check_guard", END)

                self.app = workflow.compile()
                logger.info("Compiled LangGraph Decision StateGraph successfully.")
            except Exception as e:
                logger.warning(f"LangGraph initialization note: {e}. Falling back to internal engine.")
                self.app = None

    async def run(self, initial_state: AtlasGraphState) -> AtlasGraphState:
        """Executes the Decision Intelligence Graph to completion."""
        state = dict(initial_state)

        # If compiled LangGraph application is ready
        if self.app is not None:
            try:
                final_state = await self.app.ainvoke(state)
                return final_state
            except Exception as e:
                logger.warning(f"LangGraph async invoke error ({e}); using direct state machine pipeline.")

        # Resilient direct state machine execution
        state = await node_analyze_query(state)
        
        while True:
            state = await node_hybrid_retrieve(state)
            state = await node_rerank_candidates(state)
            state = await node_grade_documents(state)
            
            branch = should_generate_or_rewrite(state)
            if branch == "synthesize_decision":
                break
            # Rewrite query and loop back to retrieval
            state = await node_rewrite_query(state)

        state = await node_synthesize_decision(state)
        state = await node_fact_check_guard(state)
        return state


decision_graph = AtlasDecisionGraph()
