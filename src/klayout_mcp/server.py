"""MCP server bootstrap."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from klayout_mcp.config import Settings
from klayout_mcp.session_store import SessionStore
from klayout_mcp.tools.layout_tools import LayoutTools

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
    repo_root = Path(__file__).resolve().parents[2]
    settings = Settings.from_root(repo_root)
    session_store = SessionStore(settings.artifact_root, settings.session_ttl_seconds)
    layout_tools = LayoutTools(settings=settings, session_store=session_store)
    implemented_tools = {
        "open_layout": layout_tools.open_layout,
        "close_session": layout_tools.close_session,
        "list_layers": layout_tools.list_layers,
    }

    server = FastMCP(name="klayout-mcp")
    for tool_name in EXPECTED_TOOLS:
        tool_fn = implemented_tools.get(tool_name, _placeholder_tool)
        server.add_tool(
            tool_fn,
            name=tool_name,
            description=f"Placeholder for {tool_name}.",
            structured_output=True,
        )
    return server
