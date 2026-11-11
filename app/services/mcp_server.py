"""Atlas Enterprise MCP (Model Context Protocol) Server.

This service implements the 'Act' (Tool Execution) pillar of the KARC framework.
It exposes tools over the standard Model Context Protocol (MCP) using SSE (Server-Sent Events)
transport, allowing LLM agents to safely invoke tools with clear boundaries.
"""

from mcp.server.mcpserver import MCPServer
from starlette.responses import HTMLResponse
from starlette.requests import Request
import uvicorn

# 1. Initialize the MCP Server with a descriptive name
mcp_server = MCPServer(name="Atlas-Enterprise-Tools")


# 2. Register Tools using the @mcp_server.tool() decorator
@mcp_server.tool()
def calculator(n1: int, n2: int) -> int:
    """Simple calculation tool to add two numbers together.
    
    Args:
        n1: First integer
        n2: Second integer
    Returns:
        The sum of n1 and n2.
    """
    return n1 + n2


@mcp_server.tool()
def search_atlas_summary(topic: str) -> str:
    """Search enterprise summary knowledge for Atlas policies and architecture.
    
    Args:
        topic: Keyword or topic to query (e.g. 'sla', 'architecture', 'security')
    Returns:
        A concise summary string of relevant enterprise knowledge.
    """
    topic_lower = topic.lower()
    if "sla" in topic_lower or "uptime" in topic_lower:
        return "Atlas Enterprise SLA: 99.95% uptime guarantee, P95 retrieval latency < 1500ms."
    elif "architecture" in topic_lower or "rag" in topic_lower:
        return "Atlas Architecture: Hybrid retrieval (pgvector dense + BM25 sparse) + LangGraph state machine."
    elif "security" in topic_lower or "compliance" in topic_lower:
        return "Atlas Security: SOC2 Type II compliant, point-in-time recovery, role-based access control."
    return f"Atlas knowledge base: Found general topic references for '{topic}'."


# 3. Create the ASGI/Starlette app using SSE transport
mcp_app = mcp_server.sse_app()


# 4. Add interactive Web Landing Page for browser visitors
async def homepage(request: Request) -> HTMLResponse:
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas MCP Tool Server</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e17;
            --bg-card: rgba(18, 26, 44, 0.75);
            --border-card: rgba(56, 189, 248, 0.2);
            --accent-cyan: #38bdf8;
            --accent-emerald: #10b981;
            --accent-purple: #a855f7;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0a0e17 80%);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .container {
            width: 100%;
            max-width: 760px;
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-card);
            border-radius: 20px;
            padding: 36px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 20px;
        }
        .title {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 9999px;
            color: var(--accent-emerald);
            font-size: 0.85rem;
            font-weight: 600;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background: var(--accent-emerald);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-emerald);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.85); }
        }
        .info-card {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 24px;
        }
        .endpoint-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            color: var(--accent-cyan);
            background: rgba(0, 0, 0, 0.35);
            padding: 10px 14px;
            border-radius: 8px;
            margin-top: 8px;
            word-break: break-all;
        }
        .section-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin: 20px 0 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .tools-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        @media (max-width: 600px) { .tools-grid { grid-template-columns: 1fr; } }
        .tool-card {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 18px;
            transition: all 0.2s ease;
        }
        .tool-card:hover {
            border-color: rgba(56, 189, 248, 0.4);
            transform: translateY(-2px);
        }
        .tool-name {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.95rem;
            color: #f1f5f9;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .tool-desc {
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.4;
        }
        .footer-links {
            margin-top: 28px;
            display: flex;
            gap: 14px;
            justify-content: flex-end;
        }
        .btn-link {
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent-cyan);
            border: 1px solid rgba(56, 189, 248, 0.25);
            transition: all 0.2s;
        }
        .btn-link:hover {
            background: rgba(56, 189, 248, 0.25);
            color: #fff;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 class="title">Atlas MCP Tool Server</h1>
                <p style="color: #64748b; font-size: 0.85rem; margin-top: 4px;">Model Context Protocol &bull; KARC Act Layer</p>
            </div>
            <div class="status-badge">
                <span class="status-dot"></span>
                <span>Active &bull; SSE</span>
            </div>
        </div>

        <div class="info-card">
            <span style="font-size: 0.85rem; color: #94a3b8;">MCP Transport Endpoint (SSE):</span>
            <div class="endpoint-row">
                <span>http://localhost:8001/sse</span>
                <span style="color: #64748b; font-size: 0.75rem;">GET / POST</span>
            </div>
        </div>

        <div class="section-title">Registered MCP Tools (2)</div>
        <div class="tools-grid">
            <div class="tool-card">
                <div class="tool-name">calculator(n1, n2)</div>
                <div class="tool-desc">Adds two numbers together. Used by agents for verified deterministic arithmetic.</div>
            </div>
            <div class="tool-card">
                <div class="tool-name">search_atlas_summary(topic)</div>
                <div class="tool-desc">Queries enterprise knowledge summaries for Atlas SLA, architecture, and security policies.</div>
            </div>
        </div>

        <div class="footer-links">
            <a href="http://localhost:8000" target="_blank" class="btn-link">Atlas Dashboard (Port 8000) &rarr;</a>
            <a href="http://localhost:8000/docs" target="_blank" class="btn-link">FastAPI Swagger Docs &rarr;</a>
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

mcp_app.add_route("/", homepage, methods=["GET"])


if __name__ == "__main__":
    print("Starting Atlas MCP Server on http://127.0.0.1:8001/sse ...")
    uvicorn.run(mcp_app, host="127.0.0.1", port=8001)
