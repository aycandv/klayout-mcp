import pytest


@pytest.mark.anyio
async def test_run_drc_script_returns_marker_summary(mcp_client, opened_violation_session, drc_script):
    result = await mcp_client.call(
        "run_drc_script",
        {
            "session_id": opened_violation_session,
            "script_path": str(drc_script),
            "script_type": "ruby",
        },
    )

    assert result["marker_count"] >= 1
    assert result["run_id"].startswith("drc_")
    assert result["artifacts"][0]["path"].endswith(".lyrdb")
