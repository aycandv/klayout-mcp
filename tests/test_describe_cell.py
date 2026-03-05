import pytest


@pytest.mark.anyio
async def test_describe_cell_returns_instance_data(mcp_client, opened_hierarchical_session):
    result = await mcp_client.call(
        "describe_cell",
        {"session_id": opened_hierarchical_session, "cell": "TOP", "depth": 1},
    )

    assert result["cell"] == "TOP"
    assert result["instances"]
    assert "shape_counts_by_layer" in result


@pytest.mark.anyio
async def test_describe_cell_returns_label_data(mcp_client, opened_label_session):
    result = await mcp_client.call(
        "describe_cell",
        {"session_id": opened_label_session, "cell": "TOP", "depth": 1},
    )

    assert result["labels"]
    assert result["labels"][0]["text"].startswith("PORT_")
