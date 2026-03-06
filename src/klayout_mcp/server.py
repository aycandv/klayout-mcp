"""MCP server bootstrap."""

from __future__ import annotations

from functools import wraps
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from klayout_mcp.config import Settings
from klayout_mcp.errors import KLayoutMCPError
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


def _error_response(error: KLayoutMCPError) -> dict[str, Any]:
    return {
        "code": error.code,
        "message": error.message,
        "details": dict(error.details),
    }


def _wrap_tool(tool_name: str, tool_fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    @wraps(tool_fn)
    def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return tool_fn(*args, **kwargs)
        except KLayoutMCPError as exc:
            return _error_response(exc)
        except Exception as exc:  # pragma: no cover - defensive guardrail
            return {
                "code": "INTERNAL_ERROR",
                "message": "Unexpected tool failure",
                "details": {
                    "tool": tool_name,
                    "error": str(exc),
                },
            }

    return wrapped


def build_server() -> FastMCP:
    """Build the MCP server with the fixed MVP tool names."""
    repo_root = Path(__file__).resolve().parents[2]
    settings = Settings.from_root(repo_root)
    session_store = SessionStore(settings.artifact_root, settings.session_ttl_seconds)
    layout_tools = LayoutTools(settings=settings, session_store=session_store)
    implemented_tools = {
        "open_layout": layout_tools.open_layout,
        "close_session": layout_tools.close_session,
        "list_cells": layout_tools.list_cells,
        "describe_cell": layout_tools.describe_cell,
        "list_layers": layout_tools.list_layers,
        "query_region": layout_tools.query_region,
        "measure_geometry": layout_tools.measure_geometry,
        "set_view": layout_tools.set_view,
        "render_view": layout_tools.render_view,
        "run_drc_script": layout_tools.run_drc_script,
        "extract_markers": layout_tools.extract_markers,
    }

    server = FastMCP(name="klayout-mcp")
    for tool_name in EXPECTED_TOOLS:
        tool_fn = implemented_tools.get(tool_name, _placeholder_tool)
        server.add_tool(
            _wrap_tool(tool_name, tool_fn),
            name=tool_name,
            description=f"KLayout MCP tool: {tool_name}.",
            structured_output=True,
        )
    return server


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
