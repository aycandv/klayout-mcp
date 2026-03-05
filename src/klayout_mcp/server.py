"""MCP server bootstrap."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

EXPECTED_TOOLS = [
    "open_layout",
    "close_session",
    "list_cells",
    "describe_cell",
    "list_layers",
    "query_region",
    "measure_geometry",
    "set_view",
    "render_view",
    "run_drc_script",
    "extract_markers",
]


def _placeholder_tool() -> dict[str, str]:
    return {"status": "not_implemented"}


def build_server() -> FastMCP:
    """Build the MCP server with the fixed MVP tool names."""
    server = FastMCP(name="klayout-mcp")
    for tool_name in EXPECTED_TOOLS:
        server.add_tool(
            _placeholder_tool,
            name=tool_name,
            description=f"Placeholder for {tool_name}.",
            structured_output=True,
        )
    return server
