import pytest


@pytest.mark.anyio
async def test_list_cells_returns_sorted_cell_names(mcp_client, opened_hierarchical_session):
    result = await mcp_client.call(
        "list_cells",
        {"session_id": opened_hierarchical_session, "max_depth": 2},
    )

    names = [cell["name"] for cell in result["cells"]]
    assert names == sorted(names)
    assert result["cells"][0]["child_instance_count"] >= 0
