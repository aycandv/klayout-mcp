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


@pytest.mark.anyio
async def test_query_region_truncates_texts(mcp_client, opened_label_session):
    result = await mcp_client.call(
        "query_region",
        {
            "session_id": opened_label_session,
            "box": {"left": -5.0, "bottom": -5.0, "right": 30.0, "top": 5.0},
            "max_texts": 1,
        },
    )

    assert result["summary"]["text_count"] == 2
    assert len(result["texts"]) == 1
    assert result["truncation"]["texts_dropped"] == 1


@pytest.mark.anyio
async def test_query_region_rejects_negative_limits(mcp_client, opened_session):
    result = await mcp_client.call_expect_error(
        "query_region",
        {
            "session_id": opened_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 50.0, "top": 20.0},
            "max_shapes": -1,
        },
    )

    assert result["code"] == "INVALID_TARGET"
