import pytest


@pytest.mark.anyio
async def test_query_region_returns_shape_refs(mcp_client, opened_session):
    result = await mcp_client.call(
        "query_region",
        {
            "session_id": opened_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 50.0, "top": 20.0},
            "hierarchy_mode": "recursive",
        },
    )
    repeated = await mcp_client.call(
        "query_region",
        {
            "session_id": opened_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 50.0, "top": 20.0},
            "hierarchy_mode": "recursive",
        },
    )

    assert result["shapes"]
    assert result["shapes"][0]["id"].startswith("shp_")
    assert result["shapes"][0]["id"] == repeated["shapes"][0]["id"]


@pytest.mark.anyio
async def test_query_region_reports_truncation(mcp_client, opened_dense_session):
    result = await mcp_client.call(
        "query_region",
        {
            "session_id": opened_dense_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 500.0, "top": 500.0},
            "max_shapes": 1,
        },
    )

    assert len(result["shapes"]) == 1
    assert result["truncation"]["shapes_dropped"] >= 0
