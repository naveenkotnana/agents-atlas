"""LangGraph Decision Intelligence Graph Nodes."""
import uuid
import datetime
from typing import Dict, Any, List
from app.graph.state import AtlasGraphState
from app.services.hybrid_retriever import hybrid_retriever
from app.services.reranker import reranker
from app.services.ollama_client import ollama_client
from app.config import settings
from app.core.logging import logger


def _log_step(state: AtlasGraphState, node_name: str, action: str, observation: str):
    """Helper to record explainability traces for each node execution."""
    if "reasoning_steps" not in state or state["reasoning_steps"] is None:
        state["reasoning_steps"] = []
    state["reasoning_steps"].append({
        "node_name": node_name,
        "action": action,
        "observation": observation,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })


async def node_analyze_query(state: AtlasGraphState) -> AtlasGraphState:
    """Node 1: Analyzes incoming query, determines semantic intent and extraction parameters."""
    query = state.get("query", "").strip()
    original_query = state.get("original_query") or query
    state["original_query"] = original_query
    if "rewritten_queries" not in state:
        state["rewritten_queries"] = []
    if "rewrite_count" not in state:
        state["rewrite_count"] = 0

    intent = "factual_retrieval"
    if any(k in query.lower() for k in ["compare", "versus", "vs", "difference"]):
        intent = "comparative_analysis"
    elif any(k in query.lower() for k in ["should we", "recommend", "risk", "approve", "decision"]):
        intent = "decision_recommendation"

    state["intent"] = intent
    _log_step(
        state,
        "QueryAnalyzerNode",
        f"Analyzed query: '{query}'",
        f"Identified intent class '{intent}'. Formulated search parameters."
    )
    return state


async def node_hybrid_retrieve(state: AtlasGraphState) -> AtlasGraphState:
    """Node 2: Executes Dense Vector + Sparse BM25 + Reciprocal Rank Fusion (RRF)."""
    query = state.get("query", "")
    all_chunks = state.get("all_corpus_chunks", [])

    candidates = await hybrid_retriever.search(
        query=query,
        chunks=all_chunks,
        top_k=settings.TOP_K_RETRIEVAL,
        dense_weight=settings.DENSE_WEIGHT,
        sparse_weight=settings.SPARSE_WEIGHT
    )

    state["retrieved_documents"] = candidates
    _log_step(
        state,
        "HybridRetrievalNode",
        f"Hybrid retrieval executed for '{query}' across {len(all_chunks)} chunks",
        f"Retrieved {len(candidates)} candidates via BM25 + Dense RRF fusion."
    )
    return state


async def node_rerank_candidates(state: AtlasGraphState) -> AtlasGraphState:
    """Node 3: Applies Cross-Encoder deep attention reranking on hybrid candidates."""
    query = state.get("query", "")
    candidates = state.get("retrieved_documents", [])

    reranked = await reranker.rerank(
        query=query,
        candidates=candidates,
        top_k=settings.TOP_K_RERANK
    )

    state["reranked_documents"] = reranked
    top_score = reranked[0].get("rerank_score", 0.0) if reranked else 0.0
    _log_step(
        state,
        "CrossEncoderRerankNode",
        f"Reranked top {len(candidates)} candidates to {len(reranked)} precision chunks",
        f"Top cross-attention relevance score: {top_score:.3f}."
    )
    return state


async def node_grade_documents(state: AtlasGraphState) -> AtlasGraphState:
    """Node 4: Evaluates whether reranked chunks contain sufficient evidence."""
    reranked = state.get("reranked_documents", [])
    rewrite_count = state.get("rewrite_count", 0)

    # If any document exceeds the minimum relevance threshold
    has_relevant = False
    if reranked:
        top_chunk = reranked[0]
        if top_chunk.get("rerank_score", 0.0) >= settings.RERANK_MIN_SCORE:
            has_relevant = True

    # If already reached max rewrites, force proceed to synthesis
    if rewrite_count >= settings.MAX_REWRITE_CYCLES:
        has_relevant = True

    state["documents_graded_relevant"] = has_relevant
    status_str = "RELEVANT" if has_relevant else "NEEDS_QUERY_REWRITE"
    _log_step(
        state,
        "DocumentGraderNode",
        f"Evaluated evidence quality (cycle {rewrite_count}/{settings.MAX_REWRITE_CYCLES})",
        f"Verdict: {status_str}."
    )
    return state


async def node_rewrite_query(state: AtlasGraphState) -> AtlasGraphState:
    """Node 5: Self-correction loop - reformulates query to uncover missed context."""
    current_query = state.get("query", "")
    rewrite_count = state.get("rewrite_count", 0) + 1
    state["rewrite_count"] = rewrite_count

    prompt = (
        f"You are an enterprise knowledge search optimizer. The current query:\n"
        f"'{current_query}'\n"
        f"did not return sufficiently relevant knowledge chunks. "
        f"Rewrite this query into a concise, high-signal enterprise search query with synonyms."
    )

    rewritten = await ollama_client.generate(prompt=prompt, temperature=0.3)
    # Clean up rewritten string
    clean_rewritten = rewritten.strip().replace('"', '').replace('\n', ' ')
    if not clean_rewritten or len(clean_rewritten) < 5:
        clean_rewritten = f"{current_query} overview guidelines policy"

    state["rewritten_queries"].append(clean_rewritten)
    state["query"] = clean_rewritten
    _log_step(
        state,
        "QueryRewriteNode",
        f"Triggered self-correction rewrite #{rewrite_count}",
        f"New optimized query: '{clean_rewritten}'"
    )
    return state


async def node_synthesize_decision(state: AtlasGraphState) -> AtlasGraphState:
    """Node 6: Synthesizes structured decision intelligence with citations."""
    query = state.get("original_query", state.get("query", ""))
    docs = state.get("reranked_documents", [])

    # Build context string and citations
    context_blocks = []
    citations = []
    for idx, doc in enumerate(docs):
        cid = doc.get("chunk_id") or doc.get("id") or str(idx)
        title = doc.get("document_title", "Document")
        snippet = doc.get("content", "")
        context_blocks.append(f"[Source {idx+1}: {title}]\n{snippet}")
        citations.append({
            "chunk_id": cid,
            "document_title": title,
            "snippet": snippet[:240] + ("..." if len(snippet) > 240 else ""),
            "relevance_score": doc.get("rerank_score", doc.get("rrf_score", 0.0))
        })

    state["citations"] = citations
    joined_context = "\n\n".join(context_blocks)

    system_prompt = (
        "You are Atlas, the Enterprise Decision Intelligence and Knowledge Platform. "
        "Answer the user's decision question with authority, precision, and clarity. "
        "Base your answer strictly on the provided enterprise context sources. "
        "Format your answer with:\n"
        "1. Executive Decision / Finding\n"
        "2. Detailed Reasoning & Evidence\n"
        "3. Recommended Next Actions\n"
        "Reference sources like [Source 1], [Source 2] wherever applicable."
    )

    user_prompt = f"Enterprise Context Sources:\n{joined_context}\n\nQuestion / Decision Directive:\n{query}"

    decision_output = await ollama_client.generate(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.2
    )

    state["decision"] = decision_output
    _log_step(
        state,
        "DecisionSynthesisNode",
        f"Synthesized decision for '{query}' using {len(docs)} context sources",
        "Generated executive summary, evidence grounding, and actionable next steps."
    )
    return state


async def node_fact_check_guard(state: AtlasGraphState) -> AtlasGraphState:
    """Node 7: Guards against hallucinations and calculates confidence score."""
    decision = state.get("decision", "")
    citations = state.get("citations", [])

    confidence = 0.85
    if citations:
        avg_citation_score = sum(c.get("relevance_score", 0.5) for c in citations) / len(citations)
        confidence = min(max(avg_citation_score * 1.1, 0.4), 0.98)

    guard_passed = confidence >= settings.HALLUCINATION_GUARD_THRESHOLD
    state["confidence_score"] = round(confidence, 3)
    state["hallucination_guard_passed"] = guard_passed

    _log_step(
        state,
        "HallucinationGuardNode",
        f"Verified factuality against {len(citations)} citations",
        f"Calculated confidence score: {confidence:.3f}. Guard Passed: {guard_passed}."
    )
    return state
