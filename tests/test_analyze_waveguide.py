import pytest


@pytest.mark.anyio
async def test_analyze_waveguide_reports_straight_path_metrics(mcp_client, queried_waveguide_region):
    target_id = queried_waveguide_region["shapes"][0]["id"]

    result = await mcp_client.call(
        "analyze_waveguide",
        {
            "session_id": queried_waveguide_region["session_id"],
            "target_id": target_id,
        },
    )

    assert result["session_id"] == queried_waveguide_region["session_id"]
    assert result["target_id"] == target_id
    assert result["kind"] == "path"
    assert result["is_path"] is True
    assert result["is_axis_aligned"] is True
    assert result["orientation"] == "horizontal"
    assert result["path_width_um"] == pytest.approx(0.5)
    assert result["segment_length_um"] == pytest.approx(40.0)
    assert result["bend_radius_estimate_um"] is None
    assert result["analysis_warnings"] == []


@pytest.mark.anyio
async def test_analyze_waveguide_reports_bend_characteristics(mcp_client, queried_bend_region):
    target_id = queried_bend_region["shapes"][0]["id"]

    result = await mcp_client.call(
        "analyze_waveguide",
        {
            "session_id": queried_bend_region["session_id"],
            "target_id": target_id,
        },
    )

    assert result["kind"] == "path"
    assert result["is_path"] is True
    assert result["is_axis_aligned"] is False
    assert result["orientation"] == "mixed"
    assert result["path_width_um"] == pytest.approx(0.5)
    assert result["segment_length_um"] == pytest.approx(24.0)
    assert result["bend_radius_estimate_um"] == pytest.approx(6.0)
    assert result["analysis_warnings"] == []
