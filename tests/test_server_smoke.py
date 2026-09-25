import pytest

from klayout_mcp.server import build_server


@pytest.mark.anyio
async def test_build_server_exposes_expected_tool_names():
    server = build_server()
    tool_names = {tool.name for tool in await server.list_tools()}
    assert "open_layout" in tool_names
    assert "analyze_waveguide" in tool_names
    assert "render_view" in tool_names


@pytest.mark.anyio
async def test_tool_descriptions_come_from_handler_docstrings():
    server = build_server()
    tools = {tool.name: tool for tool in await server.list_tools()}

    for tool in tools.values():
        assert not tool.description.startswith("KLayout MCP tool:")
        assert "Args:" in tool.description
    assert "session_id" in tools["open_layout"].description
    assert "query_region" in tools["measure_geometry"].description
