import pytest

from klayout_mcp.server import build_server


@pytest.mark.anyio
async def test_build_server_exposes_expected_tool_names():
    server = build_server()
    tool_names = {tool.name for tool in await server.list_tools()}
    assert "open_layout" in tool_names
    assert "render_view" in tool_names
