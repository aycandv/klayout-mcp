import pytest


@pytest.mark.anyio
async def test_extract_markers_can_render_crops(mcp_client, completed_drc_run):
    result = await mcp_client.call(
        "extract_markers",
        {
            "session_id": completed_drc_run["session_id"],
            "run_id": completed_drc_run["run_id"],
            "include_crops": True,
            "crop_size_um": {"x": 20.0, "y": 20.0},
        },
    )

    assert result["markers"][0]["crop"]["path"].endswith(".png")
