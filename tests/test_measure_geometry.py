import pytest


@pytest.mark.anyio
async def test_measure_geometry_reports_path_width(mcp_client, queried_waveguide_region):
    target_id = queried_waveguide_region["shapes"][0]["id"]

    result = await mcp_client.call(
        "measure_geometry",
        {
            "session_id": queried_waveguide_region["session_id"],
            "mode": "path_width",
            "target_ids": [target_id],
        },
    )

    assert result["value_um"] > 0
    assert result["value_dbu"] > 0


@pytest.mark.anyio
async def test_measure_geometry_reports_edge_gap_for_coupler(mcp_client, queried_coupler_region):
    ids = [shape["id"] for shape in queried_coupler_region["shapes"][:2]]

    result = await mcp_client.call(
        "measure_geometry",
        {
            "session_id": queried_coupler_region["session_id"],
            "mode": "edge_gap",
            "target_ids": ids,
        },
    )

    assert result["value_um"] >= 0
    assert result["value_dbu"] >= 0
