import pytest


@pytest.mark.anyio
async def test_all_contract_tool_names_exist(mcp_client):
    assert await mcp_client.list_tool_names() == {
        "open_layout",
        "close_session",
        "list_cells",
        "describe_cell",
        "list_layers",
        "query_region",
        "measure_geometry",
        "analyze_waveguide",
        "set_view",
        "render_view",
        "run_drc_script",
        "extract_markers",
    }
