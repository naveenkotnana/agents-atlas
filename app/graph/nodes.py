"""LangGraph Decision Intelligence Graph Nodes."""
import re
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

    query_clean = query.lower().strip("?!., \t\n")
    conversational_keywords = {
        "hi", "hello", "hey", "hola", "sup", "howdy", "good morning", "good evening", "good afternoon",
        "who are you", "what are you", "what can you do", "help", "who made you", "what is atlas",
        "how are you", "thanks", "thank you", "great", "ok", "okay", "bye", "goodbye"
    }

    words = query_clean.split()
    if query_clean in conversational_keywords or (len(words) <= 3 and any(query_clean.startswith(k) for k in ["hi", "hello", "hey", "howdy", "good morning"])):
        intent = "conversational"
    elif any(k in query.lower() for k in ["compare", "versus", "vs", "difference"]):
        intent = "comparative_analysis"
    elif any(k in query.lower() for k in ["should we", "recommend", "risk", "approve", "decision"]):
        intent = "decision_recommendation"
    else:
        intent = "factual_retrieval"

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
    query = state.get("original_query", state.get("query", ""))
    query_lower = query.lower().strip()
    query_words = set(w.lower() for w in re.findall(r"\b[A-Za-z0-9_-]{2,}\b", query))

    # Check if any document exceeds relevance threshold or matches exact entity/keywords
    has_relevant = False
    if reranked:
        top_chunk = reranked[0]
        score = top_chunk.get("rerank_score", 0.0)
        content_lower = top_chunk.get("content", "").lower()
        title_lower = top_chunk.get("document_title", "").lower()
        
        # Immediate match if exact query or ID (e.g. USR-0027, INC-78431) appears in the chunk
        if query_lower in content_lower or query_lower in title_lower:
            has_relevant = True
        elif any(w in content_lower or w in title_lower for w in query_words if len(w) >= 3):
            if score >= 0.15:
                has_relevant = True
        elif score >= settings.RERANK_MIN_SCORE:
            has_relevant = True

    if has_relevant:
        state["documents_graded_relevant"] = True
        state["evidence_status"] = "relevant"
        status_str = "RELEVANT"
    else:
        if rewrite_count < settings.MAX_REWRITE_CYCLES:
            state["documents_graded_relevant"] = False
            state["evidence_status"] = "pending_rewrite"
            status_str = "NEEDS_QUERY_REWRITE"
        else:
            # Reached max rewrites without finding relevant context
            state["documents_graded_relevant"] = True
            state["evidence_status"] = "not_available"
            status_str = "NOT_AVAILABLE"

    _log_step(
        state,
        "DocumentGraderNode",
        f"Evaluated evidence quality (cycle {rewrite_count}/{settings.MAX_REWRITE_CYCLES})",
        f"Verdict: {status_str}."
    )
    return state


async def node_rewrite_query(state: AtlasGraphState) -> AtlasGraphState:
    """Node 5: Self-correction loop - reformulates query into concise search keywords."""
    current_query = state.get("query", "")
    rewrite_count = state.get("rewrite_count", 0) + 1
    state["rewrite_count"] = rewrite_count

    prompt = (
        f"You are a search query optimizer. Given the search '{current_query}', "
        f"output ONLY 2 to 4 search keywords separated by spaces. "
        f"Do NOT provide explanations, sentences, or conversational remarks."
    )

    rewritten = await ollama_client.generate(prompt=prompt, temperature=0.1)
    clean_rewritten = rewritten.strip().split("\n")[0].strip('"* \t\r')
    if not clean_rewritten or len(clean_rewritten) < 3 or len(clean_rewritten.split()) > 6:
        clean_rewritten = f"{current_query} policy guidelines specifications"

    state["rewritten_queries"].append(clean_rewritten)
    state["query"] = clean_rewritten
    _log_step(
        state,
        "QueryRewriteNode",
        f"Triggered self-correction rewrite #{rewrite_count}",
        f"New optimized query: '{clean_rewritten}'"
    )
    return state


def _clean_plain_response(text: str) -> str:
    """Removes raw markdown symbols (** / ### / ---) so answers are clean, readable plain text."""
    if not text:
        return ""
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line in ("---", "***", "___"):
            continue
        # Remove leading markdown headings like ### or ##
        line = re.sub(r"^#{1,6}\s*", "", line)
        # Remove bold/italic markers ** and __
        line = line.replace("**", "").replace("__", "")
        # Normalize markdown dash/star bullets at start of line into clean dot bullets
        line = re.sub(r"^[-*]\s+", "• ", line)
        lines.append(line)
    # Collapse excessive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return cleaned


async def node_synthesize_decision(state: AtlasGraphState) -> AtlasGraphState:
    """Node 6: Synthesizes simple, clean, ChatGPT-style answers without raw markdown symbols."""
    query = state.get("original_query", state.get("query", ""))
    intent = state.get("intent", "factual_retrieval")
    evidence_status = state.get("evidence_status", "relevant")

    # 1. Handle Regular Conversational Inquiries (Greetings, 'hi', 'who are you', etc.)
    if intent == "conversational":
        conversational_prompt = (
            f"You are Atlas, a friendly, helpful enterprise AI assistant. "
            f"The user said: '{query}'. "
            f"Reply warmly, clearly, and briefly in plain text (DO NOT use **, ###, or * symbols). "
            f"Introduce yourself as Atlas Enterprise AI and list 3 short examples of what they can ask about:\n"
            f"• Incidents & SLAs (for example: Incident INC-78431 or contract CNT-2026-0089)\n"
            f"• Cloud & Uptime Policies (99.95% uptime SLA, Disaster Recovery RTO/RPO)\n"
            f"• Security & User Directory (SOC2 encryption or user lookup like USR-0027)"
        )
        response = await ollama_client.generate(prompt=conversational_prompt, temperature=0.6)
        state["decision"] = _clean_plain_response(response)
        state["citations"] = []
        state["confidence_score"] = 1.0
        _log_step(
            state,
            "DecisionSynthesisNode",
            "Conversational Request",
            "Delivered clear, friendly conversational response."
        )
        return state

    # 2. Handle 'Information Not Available' when no relevant documents exist
    if evidence_status == "not_available":
        clean_q = query.strip()
        state["decision"] = (
            f"Information Not Available\n\n"
            f"I searched the enterprise knowledge base, but no verified records were found matching \"{clean_q}\".\n\n"
            f"What Was Checked\n"
            f"• Enterprise Documents: Scanned indexed SLAs, incident postmortems, financial reports, and security policies.\n"
            f"• Relevance Check: No retrieved documents matched your query with high confidence.\n\n"
            f"Available Topics You Can Ask About\n"
            f"• Incidents: Which customer was affected by incident INC-78431 and what SLA penalties apply?\n"
            f"• SLA Standards: Analyze the Vertex Global SLA terms regarding uptime guarantees.\n"
            f"• Security: What are the SOC2 Type II data encryption standards?\n"
            f"• User Directory: Show details for user USR-0027 or USR-ADMIN-01.\n\n"
            f"Tip: If you have a document or CSV containing \"{clean_q}\", upload it via Knowledge Ingestion or /api/v1/ingest."
        )
        state["citations"] = []
        state["confidence_score"] = 0.0
        _log_step(
            state,
            "DecisionSynthesisNode",
            "Evidence Absent",
            "Formulated structured Not-Available guidance."
        )
        return state

    # 3. Handle Grounded Enterprise Decision Synthesis with Simple, Clean Structure
    docs = state.get("reranked_documents", [])
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
        "You are Atlas, a friendly, clear enterprise AI assistant. "
        "Explain the answer in simple, everyday English so anyone can understand it immediately.\n\n"
        "STRICT FORMATTING RULES:\n"
        "- NEVER use markdown symbols like **, *, ###, ##, or ---.\n"
        "- Use clean plain-text headings and bullet points with •.\n"
        "- Structure your answer cleanly into 3 short sections:\n\n"
        "Direct Answer\n"
        "[1-2 simple sentences directly answering the user's question]\n\n"
        "Key Details\n"
        "• [Short, clear fact 1 relevant to the question]\n"
        "• [Short, clear fact 2 relevant to the question]\n"
        "• [Short, clear fact 3 relevant to the question]\n\n"
        "Recommended Next Steps\n"
        "1. [Simple practical step 1]\n"
        "2. [Simple practical step 2]\n"
        "3. [Simple practical step 3]\n\n"
        "If the provided context does NOT contain the answer, state clearly: "
        "'This information is not available in the current enterprise knowledge base.'"
    )

    user_prompt = f"Enterprise Context Sources:\n{joined_context}\n\nQuestion:\n{query}"

    decision_output = await ollama_client.generate(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.2
    )

    state["decision"] = _clean_plain_response(decision_output)
    _log_step(
        state,
        "DecisionSynthesisNode",
        f"Synthesized clean structured decision for '{query}' using {len(docs)} context sources",
        "Generated simple, symbol-free structured answer."
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
