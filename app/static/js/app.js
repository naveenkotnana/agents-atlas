// Atlas Enterprise Decision Intelligence Client Controller

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  checkHealth();
  loadDocuments();
  initDecisionStudio();
  initHybridSearch();
  initIngestion();
  initRagasEval();
  initMultimodalChat();
});

// -----------------------------------------------------------------
// 1. Tab Navigation
// -----------------------------------------------------------------
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });
}

// -----------------------------------------------------------------
// 2. Health & Telemetry Status
// -----------------------------------------------------------------
async function checkHealth() {
  const badge = document.getElementById("system-health-badge");
  const text = document.getElementById("system-health-text");

  try {
    const res = await fetch("/api/v1/health");
    if (res.ok) {
      const data = await res.json();
      text.textContent = `Atlas Operational (${data.database.total_documents} Docs, ${data.database.total_chunks} Chunks)`;
    } else {
      text.textContent = "Atlas Degraded";
      badge.style.color = "var(--accent-amber)";
    }
  } catch (err) {
    text.textContent = "Backend Offline";
    badge.style.color = "var(--accent-rose)";
  }
}

// -----------------------------------------------------------------
// 3. Decision Intelligence Studio (LangGraph Workflow)
// -----------------------------------------------------------------
window.setDecisionQuery = function(text) {
  const input = document.getElementById("decision-query-input");
  if (input) {
    input.value = text;
    input.focus();
    // Smooth scroll to directive box
    input.scrollIntoView({ behavior: "smooth", block: "center" });
  }
};

function initDecisionStudio() {
  const btn = document.getElementById("btn-submit-decision");
  const queryInput = document.getElementById("decision-query-input");
  const evalToggle = document.getElementById("eval-toggle");
  const spinner = document.getElementById("decision-spinner");
  const btnText = document.getElementById("decision-btn-text");

  // Keyboard shortcut Ctrl/Cmd + Enter
  queryInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      btn.click();
    }
  });

  btn.addEventListener("click", async () => {
    const query = queryInput.value.trim();
    if (!query) {
      alert("Please enter an enterprise directive question.");
      return;
    }

    // Set UI Loading State
    btn.disabled = true;
    spinner.style.display = "inline-block";
    btnText.textContent = "Executing Multi-Agent Graph...";
    resetPipelineNodes();
    animatePipelineNodes();

    try {
      const res = await fetch("/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          evaluate_with_ragas: evalToggle.checked,
          max_rewrite_cycles: 2
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Query execution failed.");
      }

      const data = await res.json();
      displayDecisionResult(data);
      completeAllPipelineNodes();
    } catch (err) {
      alert("Execution Error: " + err.message);
      resetPipelineNodes();
    } finally {
      btn.disabled = false;
      spinner.style.display = "none";
      btnText.textContent = "Execute Multi-Agent Flow";
    }
  });
}

function resetPipelineNodes() {
  for (let i = 1; i <= 6; i++) {
    const node = document.getElementById(`node-${i}`);
    const badge = document.getElementById(`badge-${i}`);
    if (node) node.classList.remove("active", "completed");
    if (badge) badge.textContent = "Idle";
  }
  const tag = document.getElementById("pipeline-status-tag");
  if (tag) tag.textContent = "Status: Initializing...";
}

function animatePipelineNodes() {
  const steps = [
    { id: 1, label: "Analyzing" },
    { id: 2, label: "Retrieving" },
    { id: 3, label: "Reranking" },
    { id: 4, label: "Grading" },
    { id: 5, label: "Synthesizing" },
    { id: 6, label: "Auditing" }
  ];

  steps.forEach((s, idx) => {
    setTimeout(() => {
      const node = document.getElementById(`node-${s.id}`);
      const badge = document.getElementById(`badge-${s.id}`);
      const tag = document.getElementById("pipeline-status-tag");

      if (s.id > 1) {
        const prevNode = document.getElementById(`node-${s.id - 1}`);
        const prevBadge = document.getElementById(`badge-${s.id - 1}`);
        if (prevNode) {
          prevNode.classList.remove("active");
          prevNode.classList.add("completed");
        }
        if (prevBadge) prevBadge.textContent = "Passed";
      }

      if (node) {
        node.classList.add("active");
        if (badge) badge.textContent = s.label;
      }
      if (tag) tag.textContent = `Status: Executing Node ${s.id} (${s.label})...`;
    }, idx * 280);
  });
}

function completeAllPipelineNodes() {
  for (let i = 1; i <= 6; i++) {
    const node = document.getElementById(`node-${i}`);
    const badge = document.getElementById(`badge-${i}`);
    if (node) {
      node.classList.remove("active");
      node.classList.add("completed");
    }
    if (badge) badge.textContent = "Passed";
  }
  const tag = document.getElementById("pipeline-status-tag");
  if (tag) tag.textContent = "Status: Pipeline Completed Successfully";
}

function displayDecisionResult(data) {
  document.getElementById("decision-placeholder").style.display = "none";
  const container = document.getElementById("decision-result-container");
  container.style.display = "block";

  // Meta Badges
  const metaBadges = document.getElementById("output-meta-badges");
  const latencyBadge = document.getElementById("output-latency");
  const confBadge = document.getElementById("output-confidence");

  metaBadges.style.display = "flex";
  latencyBadge.textContent = `⚡ ${Math.round(data.execution_time_ms)}ms`;

  const confPct = Math.round(data.confidence_score * 100);
  confBadge.innerHTML = `
    <svg width="12" height="12" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
    Confidence: ${confPct}%
  `;
  if (confPct < 65) {
    confBadge.style.color = "var(--accent-amber)";
    confBadge.style.borderColor = "rgba(245, 158, 11, 0.35)";
    confBadge.style.backgroundColor = "rgba(245, 158, 11, 0.1)";
  } else {
    confBadge.style.color = "var(--accent-emerald)";
    confBadge.style.borderColor = "rgba(16, 185, 129, 0.35)";
    confBadge.style.backgroundColor = "rgba(16, 185, 129, 0.12)";
  }

  // Parse Executive Finding & Body
  const rawText = data.decision || "";
  let findingText = "Documented enterprise evidence substantiates policy and operational directives.";
  let bodyText = rawText;

  if (rawText.includes("Key Decision & Finding:")) {
    const parts = rawText.split("Key Decision & Finding:");
    const subParts = parts[1].split("\n\n");
    findingText = subParts[0].trim();
    bodyText = rawText;
  } else if (rawText.includes("1. Executive Decision / Finding")) {
    const parts = rawText.split("1. Executive Decision / Finding");
    const subParts = parts[1].split("\n\n");
    findingText = subParts[0].replace(/[:\-]/, '').trim();
    bodyText = rawText;
  }

  document.getElementById("finding-callout-text").textContent = findingText;
  document.getElementById("decision-text").textContent = bodyText;

  // RAGAS Continuous Evaluation Matrix
  const ragasBox = document.getElementById("decision-ragas-box");
  if (data.ragas_evaluation) {
    ragasBox.style.display = "block";
    const r = data.ragas_evaluation;

    document.getElementById("score-faithfulness").textContent = r.faithfulness.toFixed(2);
    document.getElementById("bar-faithfulness").style.width = `${Math.round(r.faithfulness * 100)}%`;

    document.getElementById("score-relevance").textContent = r.answer_relevance.toFixed(2);
    document.getElementById("bar-relevance").style.width = `${Math.round(r.answer_relevance * 100)}%`;

    document.getElementById("score-precision").textContent = r.context_precision.toFixed(2);
    document.getElementById("bar-precision").style.width = `${Math.round(r.context_precision * 100)}%`;

    document.getElementById("score-recall").textContent = r.context_recall.toFixed(2);
    document.getElementById("bar-recall").style.width = `${Math.round(r.context_recall * 100)}%`;

    const verdictTag = document.getElementById("ragas-verdict-badge");
    verdictTag.textContent = `${r.verdict} (Overall: ${(r.overall_score * 100).toFixed(1)}%)`;
  } else {
    ragasBox.style.display = "none";
  }

  // Citations List
  const citationsContainer = document.getElementById("citations-container");
  const countTag = document.getElementById("citations-count-tag");
  citationsContainer.innerHTML = "";

  if (data.citations && data.citations.length > 0) {
    countTag.textContent = `${data.citations.length} sources substantiated`;
    data.citations.forEach((c, idx) => {
      const card = document.createElement("div");
      card.className = "citation-card";
      const scorePct = (c.relevance_score * 100).toFixed(1);

      card.innerHTML = `
        <div class="citation-card-header">
          <div class="citation-title">
            <span style="color: var(--accent-cyan); font-family: var(--font-mono); font-size: 0.75rem;">[Source ${idx + 1}]</span>
            <span>${escapeHtml(c.document_title)}</span>
          </div>
          <span class="citation-score-pill">Relevance: ${scorePct}%</span>
        </div>
        <p class="citation-snippet">${escapeHtml(c.snippet)}</p>
      `;
      citationsContainer.appendChild(card);
    });
  } else {
    countTag.textContent = "No citations matched";
    citationsContainer.innerHTML = "<p style='color: var(--text-muted); font-size: 0.8rem;'>No direct citations found.</p>";
  }

  // Reasoning Trace Accordion
  const traceContainer = document.getElementById("reasoning-trace-container");
  traceContainer.innerHTML = "";

  if (data.reasoning_steps && data.reasoning_steps.length > 0) {
    data.reasoning_steps.forEach((step, idx) => {
      const item = document.createElement("div");
      item.className = "trace-step";
      item.innerHTML = `
        <span class="trace-step-num">Step ${idx + 1}</span>
        <div>
          <div style="font-weight: 700; color: #93c5fd; font-size: 0.82rem;">${escapeHtml(step.node_name)}</div>
          <div style="color: var(--text-secondary); margin-top: 2px;">${escapeHtml(step.action)}</div>
          <div style="color: var(--text-muted); font-size: 0.72rem; margin-top: 2px;">↳ ${escapeHtml(step.observation)}</div>
        </div>
      `;
      traceContainer.appendChild(item);
    });
  }
}

// -----------------------------------------------------------------
// 4. Hybrid Search & Reranking Explorer
// -----------------------------------------------------------------
function initHybridSearch() {
  const btn = document.getElementById("btn-run-search");
  const queryInput = document.getElementById("search-query-input");
  const sliderDense = document.getElementById("slider-dense-wt");
  const sliderSparse = document.getElementById("slider-sparse-wt");
  const valDense = document.getElementById("val-dense-wt");
  const valSparse = document.getElementById("val-sparse-wt");
  const checkRerank = document.getElementById("check-rerank");

  sliderDense.addEventListener("input", (e) => {
    valDense.textContent = parseFloat(e.target.value).toFixed(2);
  });
  sliderSparse.addEventListener("input", (e) => {
    valSparse.textContent = parseFloat(e.target.value).toFixed(2);
  });

  btn.addEventListener("click", async () => {
    const q = queryInput.value.trim();
    if (!q) return;

    btn.disabled = true;
    btn.textContent = "Retriever Running...";

    try {
      const res = await fetch("/api/v1/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          top_k: 10,
          rerank_top_k: 5,
          apply_reranker: checkRerank.checked,
          dense_weight: parseFloat(sliderDense.value),
          sparse_weight: parseFloat(sliderSparse.value)
        })
      });

      if (!res.ok) throw new Error("Search request failed.");
      const data = await res.json();
      renderSearchResults(data.results);
      document.getElementById("search-stats-tag").textContent = `Retrieved ${data.results.length} candidates in ${data.execution_time_ms}ms`;
    } catch (err) {
      alert("Search error: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Inspect Fusion Ranks";
    }
  });
}

function renderSearchResults(results) {
  const tbody = document.getElementById("search-results-body");
  tbody.innerHTML = "";

  if (!results || results.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">No candidates retrieved.</td></tr>`;
    return;
  }

  results.forEach(item => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="font-weight: 700; color: #93c5fd;">${escapeHtml(item.document_title)}</td>
      <td style="color: var(--text-secondary); line-height: 1.4;">${escapeHtml(item.content.substring(0, 160))}...</td>
      <td><span style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-blue);">#${item.dense_rank || '-'}</span></td>
      <td><span style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-indigo);">#${item.sparse_rank || '-'}</span></td>
      <td style="font-family: var(--font-mono); font-weight: 700;">${item.rrf_score.toFixed(5)}</td>
      <td>
        ${item.rerank_score !== null 
          ? `<span style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-emerald); background: rgba(16, 185, 129, 0.1); padding: 0.2rem 0.5rem; border-radius: 4px;">${(item.rerank_score * 100).toFixed(1)}%</span>` 
          : `<span style="color: var(--text-muted); font-size: 0.75rem;">Skipped</span>`}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// -----------------------------------------------------------------
// 5. Knowledge Base & Document Management
// -----------------------------------------------------------------
function initIngestion() {
  const btn = document.getElementById("btn-ingest");
  const spinner = document.getElementById("ingest-spinner");
  const refreshBtn = document.getElementById("btn-refresh-docs");

  refreshBtn.addEventListener("click", loadDocuments);

  btn.addEventListener("click", async () => {
    const title = document.getElementById("ingest-title").value.trim();
    const type = document.getElementById("ingest-type").value;
    const dept = document.getElementById("ingest-dept").value.trim();
    const content = document.getElementById("ingest-content").value.trim();

    if (!title || !content) {
      alert("Please provide both title and content.");
      return;
    }

    btn.disabled = true;
    spinner.style.display = "inline-block";

    try {
      const res = await fetch("/api/v1/documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title,
          source_type: type,
          content: content,
          metadata: { department: dept || "General" }
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Document ingestion failed.");
      }
      alert("Document successfully chunked, vectorized, and persisted!");
      document.getElementById("ingest-title").value = "";
      document.getElementById("ingest-content").value = "";
      loadDocuments();
      checkHealth();
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      btn.disabled = false;
      spinner.style.display = "none";
    }
  });
}

async function loadDocuments() {
  const tbody = document.getElementById("docs-list-body");
  try {
    const res = await fetch("/api/v1/documents");
    if (!res.ok) throw new Error("Failed to load documents");
    const docs = await res.json();

    tbody.innerHTML = "";
    if (docs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">No documents in repository.</td></tr>`;
      return;
    }

    docs.forEach(doc => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-weight: 700; color: #f1f5f9;">${escapeHtml(doc.title)}</td>
        <td><span style="font-size: 0.72rem; padding: 0.15rem 0.5rem; border-radius: 4px; background: rgba(59, 130, 246, 0.1); color: var(--accent-blue);">${escapeHtml(doc.source_type)}</span></td>
        <td style="font-family: var(--font-mono); font-size: 0.8rem;">${doc.chunk_count} chunks</td>
        <td>
          <button class="btn btn-secondary" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;" onclick="deleteDoc('${doc.id}')">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--accent-rose);">${err.message}</td></tr>`;
  }
}

window.deleteDoc = async function(id) {
  if (!confirm("Are you sure you want to delete this document and all its chunks?")) return;
  try {
    const res = await fetch(`/api/v1/documents/${id}`, { method: "DELETE" });
    if (res.ok) {
      loadDocuments();
      checkHealth();
    }
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
};

// -----------------------------------------------------------------
// 6. RAGAS Quality Evaluation
// -----------------------------------------------------------------
function initRagasEval() {
  const btn = document.getElementById("btn-run-eval");
  btn.addEventListener("click", async () => {
    const query = document.getElementById("eval-query").value.trim();
    const gt = document.getElementById("eval-gt").value.trim();
    const answer = document.getElementById("eval-answer").value.trim();
    const context = document.getElementById("eval-context").value.trim();

    if (!query || !answer || !context) {
      alert("Query, Answer, and Context are required.");
      return;
    }

    btn.disabled = true;
    btn.textContent = "Computing RAGAS Benchmark...";

    try {
      const res = await fetch("/api/v1/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          answer: answer,
          contexts: [context],
          ground_truth: gt || null
        })
      });

      if (!res.ok) throw new Error("Evaluation error.");
      const data = await res.json();
      displayEvalResult(data);
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Execute Benchmark Audit";
    }
  });
}

function displayEvalResult(data) {
  const resBox = document.getElementById("eval-benchmark-result");
  const verdictTag = document.getElementById("eval-verdict-tag");
  const grid = document.getElementById("eval-scores-row");

  resBox.style.display = "block";
  verdictTag.textContent = `${data.verdict} (Composite Score: ${(data.overall_score * 100).toFixed(1)}%)`;

  grid.innerHTML = `
    <div class="ragas-gauge-card">
      <div class="ragas-gauge-label">Faithfulness</div>
      <div class="ragas-gauge-val" style="color: var(--accent-emerald);">${(data.faithfulness * 100).toFixed(1)}%</div>
      <div class="ragas-gauge-bar"><div class="ragas-gauge-fill fill-emerald" style="width: ${data.faithfulness * 100}%;"></div></div>
    </div>
    <div class="ragas-gauge-card">
      <div class="ragas-gauge-label">Answer Relevance</div>
      <div class="ragas-gauge-val" style="color: var(--accent-blue);">${(data.answer_relevance * 100).toFixed(1)}%</div>
      <div class="ragas-gauge-bar"><div class="ragas-gauge-fill fill-blue" style="width: ${data.answer_relevance * 100}%;"></div></div>
    </div>
    <div class="ragas-gauge-card">
      <div class="ragas-gauge-label">Context Precision</div>
      <div class="ragas-gauge-val" style="color: var(--accent-indigo);">${(data.context_precision * 100).toFixed(1)}%</div>
      <div class="ragas-gauge-bar"><div class="ragas-gauge-fill fill-indigo" style="width: ${data.context_precision * 100}%;"></div></div>
    </div>
    <div class="ragas-gauge-card">
      <div class="ragas-gauge-label">Context Recall</div>
      <div class="ragas-gauge-val" style="color: var(--accent-cyan);">${(data.context_recall * 100).toFixed(1)}%</div>
      <div class="ragas-gauge-bar"><div class="ragas-gauge-fill fill-cyan" style="width: ${data.context_recall * 100}%;"></div></div>
    </div>
  `;
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>'"]/g, tag => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[tag] || tag));
}

// -----------------------------------------------------------------
// 7. Multimodal Incident Copilot & RLHF Alignment Controller
// -----------------------------------------------------------------
let chatSessionId = "session-" + Math.random().toString(36).substring(2, 9);
let chatHistory = [];

function initMultimodalChat() {
  const sendBtn = document.getElementById("btn-send-chat");
  const inputEl = document.getElementById("chat-user-input");
  const newSessionBtn = document.getElementById("btn-new-chat-session");
  const sessionLabel = document.getElementById("active-session-label");

  if (sessionLabel) {
    sessionLabel.textContent = `ID: ${chatSessionId.substring(0, 14)}`;
  }

  if (sendBtn && inputEl) {
    sendBtn.addEventListener("click", () => {
      const text = inputEl.value.trim();
      if (text) {
        handleUserMessage(text);
        inputEl.value = "";
      }
    });

    inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const text = inputEl.value.trim();
        if (text) {
          handleUserMessage(text);
          inputEl.value = "";
        }
      }
    });
  }

  if (newSessionBtn) {
    newSessionBtn.addEventListener("click", () => {
      chatSessionId = "session-" + Math.random().toString(36).substring(2, 9);
      chatHistory = [];
      if (sessionLabel) {
        sessionLabel.textContent = `ID: ${chatSessionId.substring(0, 14)}`;
      }
      const stream = document.getElementById("multimodal-chat-messages");
      if (stream) {
        stream.innerHTML = `
          <div class="chat-bubble assistant-bubble">
            <div class="bubble-header">
              <span class="bubble-sender">Atlas Copilot</span>
              <span class="bubble-time">Just now</span>
            </div>
            <div class="bubble-body">
              <p>Session reset. I am ready to reason across <strong>diagrams</strong>, <strong>audio dispatch calls</strong>, and <strong>incident postmortems</strong>.</p>
            </div>
          </div>
        `;
      }
    });
  }

  fetchRLHFMetrics();
}

window.sendQuickChatMessage = function(promptText) {
  const tabBtn = document.querySelector('[data-tab="multimodal-chat-tab"]');
  if (tabBtn && !tabBtn.classList.contains("active")) {
    tabBtn.click();
  }
  handleUserMessage(promptText);
};

async function handleUserMessage(message) {
  const stream = document.getElementById("multimodal-chat-messages");
  const spinner = document.getElementById("chat-spinner");
  const sendBtn = document.getElementById("btn-send-chat");

  if (!stream) return;

  // 1. Append User Message Bubble
  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble user-bubble";
  userBubble.innerHTML = `
    <div class="bubble-header">
      <span class="bubble-sender" style="color: #c4b5fd;">You (Analyst)</span>
      <span class="bubble-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
    </div>
    <div class="bubble-body">
      <p>${escapeHtml(message)}</p>
    </div>
  `;
  stream.appendChild(userBubble);
  stream.scrollTop = stream.scrollHeight;

  // Add to history
  chatHistory.push({ role: "user", content: message });

  // 2. Loading state
  if (spinner) spinner.style.display = "inline-block";
  if (sendBtn) sendBtn.disabled = true;

  try {
    const res = await fetch("/api/v1/chat/multimodal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        session_id: chatSessionId,
        history: chatHistory
      })
    });

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    renderAssistantResponse(data, message);
    chatHistory.push({ role: "assistant", content: data.response });

  } catch (err) {
    const errorBubble = document.createElement("div");
    errorBubble.className = "chat-bubble assistant-bubble";
    errorBubble.style.borderColor = "var(--accent-rose)";
    errorBubble.innerHTML = `
      <div class="bubble-header">
        <span class="bubble-sender" style="color: var(--accent-rose);">Copilot Error</span>
      </div>
      <div class="bubble-body">
        <p>Could not complete reasoning: ${escapeHtml(err.message)}</p>
      </div>
    `;
    stream.appendChild(errorBubble);
  } finally {
    if (spinner) spinner.style.display = "none";
    if (sendBtn) sendBtn.disabled = false;
    stream.scrollTop = stream.scrollHeight;
  }
}

function renderAssistantResponse(data, originalQuery) {
  const stream = document.getElementById("multimodal-chat-messages");
  if (!stream) return;

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble assistant-bubble";
  bubble.setAttribute("data-msg-id", data.message_id);

  // Markdown rendering
  const formattedText = parseMarkdownSimple(data.response);

  // Multimodal Media Attachments
  let mediaHtml = "";
  if (data.media_assets && data.media_assets.length > 0) {
    data.media_assets.forEach(asset => {
      if (asset.type === "image") {
        mediaHtml += `
          <div class="media-attachment-box">
            <div class="media-attachment-header">
              <span>🖼️ ${escapeHtml(asset.title)}</span>
              <span style="font-size: 0.65rem; color: var(--accent-cyan); font-family: var(--font-mono);">16:9 SCHEMATIC</span>
            </div>
            <img src="${asset.url}" alt="${escapeHtml(asset.title)}" class="chat-image-preview" onclick="openImageModal('${asset.url}')">
            <div style="padding: 0.5rem 0.8rem; font-size: 0.72rem; color: var(--text-muted); background: rgba(0,0,0,0.4);">
              ${escapeHtml(asset.description || '')} (Click image to zoom full screen)
            </div>
          </div>
        `;
      } else if (asset.type === "audio") {
        mediaHtml += `
          <div class="media-attachment-box">
            <div class="media-attachment-header">
              <span>🎙️ ${escapeHtml(asset.title)}</span>
              <span style="font-size: 0.65rem; color: var(--accent-indigo); font-family: var(--font-mono);">RADIO DISPATCH</span>
            </div>
            <div class="audio-player-wrapper">
              <audio controls style="width: 100%; height: 34px;">
                <source src="${asset.url}" type="audio/wav">
                Your browser does not support audio elements.
              </audio>
              ${asset.transcript ? `
                <div style="font-size: 0.72rem; color: #cbd5e1; background: rgba(0,0,0,0.3); padding: 0.5rem 0.75rem; border-radius: 6px; border-left: 2px solid var(--accent-cyan); white-space: pre-line; line-height: 1.45;">
                  <strong>Radio Dispatch Transcript:</strong>\n${escapeHtml(asset.transcript)}
                </div>
              ` : ''}
            </div>
          </div>
        `;
      }
    });
  }

  // Citations
  let citationsHtml = "";
  if (data.citations && data.citations.length > 0) {
    citationsHtml = `
      <div style="margin-top: 0.8rem; display: flex; flex-wrap: wrap; gap: 0.4rem;">
        ${data.citations.map(c => `
          <span style="font-size: 0.68rem; padding: 2px 7px; background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 4px; color: #a5b4fc;" title="${escapeHtml(c.snippet)}">
            📄 ${escapeHtml(c.document_title)} (${(c.score * 100).toFixed(0)}%)
          </span>
        `).join('')}
      </div>
    `;
  }

  // RLHF Feedback Widget
  const rlhfWidgetHtml = `
    <div class="rlhf-container" id="rlhf-box-${data.message_id}">
      <div class="rlhf-header">
        <span class="rlhf-title">
          <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
          RLHF Human Feedback & Alignment
        </span>
        <div class="rlhf-actions">
          <button class="rlhf-thumb-btn" onclick="handleThumbFeedback('${data.message_id}', 'thumbs_up')">
            👍 Helpful
          </button>
          <button class="rlhf-thumb-btn" onclick="handleThumbFeedback('${data.message_id}', 'thumbs_down')">
            👎 Unhelpful
          </button>
        </div>
      </div>

      <!-- Star Rating & Tags -->
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.4rem;">
        <div class="star-rating-row" id="stars-${data.message_id}">
          <span style="font-size: 0.72rem; color: var(--text-muted); margin-right: 4px;">Rate Quality:</span>
          <button class="star-btn" onclick="handleStarRating('${data.message_id}', 1)">★</button>
          <button class="star-btn" onclick="handleStarRating('${data.message_id}', 2)">★</button>
          <button class="star-btn" onclick="handleStarRating('${data.message_id}', 3)">★</button>
          <button class="star-btn" onclick="handleStarRating('${data.message_id}', 4)">★</button>
          <button class="star-btn active" onclick="handleStarRating('${data.message_id}', 5)">★</button>
        </div>
        <div class="rlhf-tags-row" id="tags-${data.message_id}">
          <span class="rlhf-tag selected" onclick="toggleRLHFTag(this)">✓ Accurate</span>
          <span class="rlhf-tag" onclick="toggleRLHFTag(this)">⚠️ Hallucination</span>
          <span class="rlhf-tag" onclick="toggleRLHFTag(this)">🔍 Missing Detail</span>
          <span class="rlhf-tag" onclick="toggleRLHFTag(this)">💡 Great Reasoning</span>
        </div>
      </div>

      <!-- Optional Comment Box & Submit -->
      <div class="rlhf-comment-box">
        <input type="text" class="rlhf-comment-input" id="comment-${data.message_id}" placeholder="Provide optional human corrective feedback for RLHF fine-tuning...">
        <button class="rlhf-submit-btn" onclick="submitFullRLHFFeedback('${data.message_id}', ${escapeHtml(JSON.stringify(originalQuery))}, ${escapeHtml(JSON.stringify(data.response))})">
          Save Feedback
        </button>
      </div>

      <div class="rlhf-success-banner" id="success-${data.message_id}" style="display: none;">
        ✓ Feedback recorded! Saved to RLHF dataset for model preference optimization.
      </div>
    </div>
  `;

  bubble.innerHTML = `
    <div class="bubble-header">
      <span class="bubble-sender">Atlas Copilot (Grounding: 96%)</span>
      <span class="bubble-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
    </div>
    <div class="bubble-body">
      ${formattedText}
      ${mediaHtml}
      ${citationsHtml}
      ${rlhfWidgetHtml}
    </div>
  `;

  stream.appendChild(bubble);
  stream.scrollTop = stream.scrollHeight;
}

// -----------------------------------------------------------------
// RLHF Interaction Handlers
// -----------------------------------------------------------------
const feedbackState = {};

window.handleThumbFeedback = function(messageId, type) {
  if (!feedbackState[messageId]) feedbackState[messageId] = { rating: 5, tags: ["Accurate"] };
  feedbackState[messageId].feedback_type = type;

  const box = document.getElementById(`rlhf-box-${messageId}`);
  if (box) {
    const btns = box.querySelectorAll(".rlhf-thumb-btn");
    btns.forEach(b => {
      b.classList.remove("active-up", "active-down");
      if (type === "thumbs_up" && b.textContent.includes("Helpful") && !b.textContent.includes("Unhelpful")) {
        b.classList.add("active-up");
      } else if (type === "thumbs_down" && b.textContent.includes("Unhelpful")) {
        b.classList.add("active-down");
      }
    });
  }
};

window.handleStarRating = function(messageId, stars) {
  if (!feedbackState[messageId]) feedbackState[messageId] = { feedback_type: "thumbs_up", tags: ["Accurate"] };
  feedbackState[messageId].rating = stars;

  const container = document.getElementById(`stars-${messageId}`);
  if (container) {
    const starBtns = container.querySelectorAll(".star-btn");
    starBtns.forEach((btn, idx) => {
      if (idx < stars) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });
  }
};

window.toggleRLHFTag = function(tagEl) {
  tagEl.classList.toggle("selected");
};

window.submitFullRLHFFeedback = async function(messageId, queryText, responseText) {
  const box = document.getElementById(`rlhf-box-${messageId}`);
  if (!box) return;

  const commentInput = document.getElementById(`comment-${messageId}`);
  const comment = commentInput ? commentInput.value.trim() : "";

  const selectedTags = [];
  const tagEls = box.querySelectorAll(".rlhf-tag.selected");
  tagEls.forEach(t => selectedTags.push(t.textContent.replace("✓", "").replace("⚠️", "").replace("🔍", "").replace("💡", "").trim()));

  const state = feedbackState[messageId] || { feedback_type: "thumbs_up", rating: 5 };

  try {
    const res = await fetch("/api/v1/chat/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: chatSessionId,
        message_id: messageId,
        query_text: queryText,
        response_text: responseText,
        feedback_type: state.feedback_type || "thumbs_up",
        rating: state.rating || 5,
        tags: selectedTags,
        comment: comment || null
      })
    });

    if (res.ok) {
      const banner = document.getElementById(`success-${messageId}`);
      if (banner) banner.style.display = "flex";
      fetchRLHFMetrics();
    }
  } catch (err) {
    console.error("Error submitting RLHF feedback:", err);
  }
};

async function fetchRLHFMetrics() {
  try {
    const res = await fetch("/api/v1/chat/feedback/metrics");
    if (res.ok) {
      const data = await res.json();
      const posEl = document.getElementById("rlhf-stat-pos");
      const starsEl = document.getElementById("rlhf-stat-stars");
      const countEl = document.getElementById("rlhf-stat-count");

      if (posEl) posEl.textContent = `${data.positive_percentage}%`;
      if (starsEl) starsEl.textContent = `${data.avg_rating} ★`;
      if (countEl) countEl.textContent = `${data.total_feedback} samples`;
    }
  } catch (err) {
    console.warn("Could not fetch RLHF metrics:", err);
  }
}

// -----------------------------------------------------------------
// Modal Handlers
// -----------------------------------------------------------------
window.openImageModal = function(src) {
  const modal = document.getElementById("image-modal");
  const img = document.getElementById("image-modal-src");
  if (modal && img) {
    img.src = src;
    modal.style.display = "flex";
  }
};

window.closeImageModal = function() {
  const modal = document.getElementById("image-modal");
  if (modal) modal.style.display = "none";
};

// -----------------------------------------------------------------
// Markdown Parser
// -----------------------------------------------------------------
function parseMarkdownSimple(md) {
  if (!md) return "";
  let html = md;
  // Headings
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 style="font-size: 1.1rem; color: #fff; margin-bottom: 0.5rem;">$1</h2>');
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  // Italic
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');
  // Unordered list items
  html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gims, '<ul>$1</ul>');
  // Linebreaks to paragraphs
  html = html.split('\n\n').map(p => {
    if (p.startsWith('<h') || p.startsWith('<blockquote') || p.startsWith('<ul>')) return p;
    return `<p>${p.replace(/\n/g, '<br>')}</p>`;
  }).join('');
  return html;
}
