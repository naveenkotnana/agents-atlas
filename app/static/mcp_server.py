"""Atlas MCP Server Entrypoint.

NOTE: Python services should typically reside in `app/services/`.
This file is provided for quick standalone execution or testing of the MCP server.
See also: `app/services/mcp_server.py`
"""

from app.services.mcp_server import mcp_server, mcp_app, calculator
import uvicorn

if __name__ == "__main__":
    # Runs the MCP SSE tool server on port 8001
    print("Starting Atlas MCP Server on http://127.0.0.1:8001/sse ...")
    uvicorn.run(mcp_app, host="[IP_ADDRESS]", port=8001)    