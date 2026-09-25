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


@pytest.mark.anyio
async def test_list_cells_max_depth_limits_hierarchy(mcp_client, opened_hierarchical_session):
    top_only = await mcp_client.call(
        "list_cells",
        {"session_id": opened_hierarchical_session, "max_depth": 0},
    )
    one_level = await mcp_client.call(
        "list_cells",
        {"session_id": opened_hierarchical_session, "max_depth": 1},
    )
    unlimited = await mcp_client.call("list_cells", {"session_id": opened_hierarchical_session})

    assert [cell["name"] for cell in top_only["cells"]] == ["TOP"]
    assert [cell["name"] for cell in one_level["cells"]] == ["CHILD", "TOP"]
    assert [cell["name"] for cell in unlimited["cells"]] == ["CHILD", "TOP"]


@pytest.mark.anyio
async def test_list_cells_rejects_negative_max_depth(mcp_client, opened_hierarchical_session):
    result = await mcp_client.call_expect_error(
        "list_cells",
        {"session_id": opened_hierarchical_session, "max_depth": -1},
    )

    assert result["code"] == "INVALID_TARGET"
