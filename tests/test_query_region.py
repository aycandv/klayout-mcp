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


@pytest.mark.anyio
async def test_query_region_ids_stay_valid_after_later_queries(mcp_client, opened_dense_session):
    first = await mcp_client.call(
        "query_region",
        {
            "session_id": opened_dense_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 3.5, "top": 1.0},
        },
    )
    await mcp_client.call(
        "query_region",
        {
            "session_id": opened_dense_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 500.0, "top": 500.0},
            "max_shapes": 1,
        },
    )
    measured = await mcp_client.call(
        "measure_geometry",
        {
            "session_id": opened_dense_session,
            "mode": "edge_gap",
            "target_ids": [shape["id"] for shape in first["shapes"]],
        },
    )

    assert measured["value_um"] == 1.0


@pytest.mark.anyio
async def test_query_region_does_not_cache_truncated_shapes(
    mcp_client,
    generated_dense_layout,
):
    box = {"left": 0.0, "bottom": 0.0, "right": 500.0, "top": 500.0}
    reference = await mcp_client.call("open_layout", {"path": str(generated_dense_layout.path)})
    everything = await mcp_client.call(
        "query_region",
        {"session_id": reference["session_id"], "box": box},
    )
    opened = await mcp_client.call("open_layout", {"path": str(generated_dense_layout.path)})
    truncated = await mcp_client.call(
        "query_region",
        {"session_id": opened["session_id"], "box": box, "max_shapes": 1},
    )
    returned_id = truncated["shapes"][0]["id"]
    dropped_id = next(
        shape["id"] for shape in everything["shapes"] if shape["id"] != returned_id
    )

    result = await mcp_client.call_expect_error(
        "measure_geometry",
        {
            "session_id": opened["session_id"],
            "mode": "edge_gap",
            "target_ids": [returned_id, dropped_id],
        },
    )

    assert result["code"] == "INVALID_TARGET"
    assert result["details"]["target_id"] == dropped_id
