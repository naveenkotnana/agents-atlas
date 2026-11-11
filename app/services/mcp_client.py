"""Atlas Enterprise MCP (Model Context Protocol) Client.

Connects to the Atlas MCP Server over SSE transport to discover
and execute tools (e.g. calculator, enterprise knowledge search).
"""

import asyncio
from typing import Any, Dict, List
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


class AtlasMCPClient:
    """Simple client to connect to an MCP Server over SSE."""

    def __init__(self, server_url: str = "http://127.0.0.1:8001/sse"):
        self.server_url = server_url

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools registered on the MCP server."""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.list_tools()
                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": getattr(tool, "input_schema", getattr(tool, "inputSchema", None)),
                    }
                    for tool in response.tools
                ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call any registered tool by name with arguments."""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.content and len(result.content) > 0:
                    return result.content[0].text
                return result.structured_content

    async def call_calculator(self, n1: int, n2: int) -> int:
        """Helper to invoke the calculator tool."""
        res_text = await self.call_tool("calculator", {"n1": n1, "n2": n2})
        return int(res_text)

    # Synchronous helpers for non-async environments
    def sync_call_calculator(self, n1: int, n2: int) -> int:
        return asyncio.run(self.call_calculator(n1, n2))

    def sync_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        return asyncio.run(self.call_tool(tool_name, arguments))


# Global default client instance
mcp_client = AtlasMCPClient()


async def demo():
    print(f"Connecting to MCP Server at {mcp_client.server_url} ...")
    try:
        tools = await mcp_client.list_tools()
        print("\n=== Available Tools ===")
        for t in tools:
            print(f"- {t['name']}: {t['description']}")

        print("\n=== Calling Calculator Tool ===")
        calc_result = await mcp_client.call_calculator(15, 27)
        print(f"calculator(15, 27) -> {calc_result}")

        print("\n=== Calling Search Tool ===")
        search_result = await mcp_client.call_tool("search_atlas_summary", {"topic": "sla"})
        print(f"search_atlas_summary('sla') -> {search_result}")

    except Exception as e:
        print(f"\n[Error connecting to MCP Server]: {e}")
        print("Tip: Make sure the server is running with: python -m app.services.mcp_server")


if __name__ == "__main__":
    asyncio.run(demo())