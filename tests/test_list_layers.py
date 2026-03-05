import pytest


@pytest.mark.anyio
async def test_list_layers_reports_numeric_layers(mcp_client, generated_layout):
    opened = await mcp_client.call("open_layout", {"path": str(generated_layout.path)})

    result = await mcp_client.call("list_layers", {"session_id": opened["session_id"]})

    assert result["layers"][0]["layer"] >= 0
    assert result["layers"][0]["datatype"] >= 0
