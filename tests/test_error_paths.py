import pytest


@pytest.mark.anyio
async def test_invalid_path_returns_contract_error_code(mcp_client):
    result = await mcp_client.call_expect_error("open_layout", {"path": "/tmp/missing.gds"})
    assert result["code"] == "FILE_NOT_FOUND"
    assert isinstance(result["details"], dict)


@pytest.mark.anyio
async def test_missing_session_returns_contract_error_code(mcp_client):
    result = await mcp_client.call_expect_error("list_layers", {"session_id": "ses_missing"})
    assert result["code"] == "SESSION_NOT_FOUND"


@pytest.mark.anyio
async def test_disallowed_drc_script_returns_contract_error_code(mcp_client, opened_session):
    result = await mcp_client.call_expect_error(
        "run_drc_script",
        {
            "session_id": opened_session,
            "script_path": "/tmp/deck.drc",
            "script_type": "ruby",
        },
    )
    assert result["code"] == "FILE_NOT_FOUND"


@pytest.mark.anyio
async def test_analyze_waveguide_rejects_unknown_target_id(mcp_client, opened_session):
    result = await mcp_client.call_expect_error(
        "analyze_waveguide",
        {
            "session_id": opened_session,
            "target_id": "shp_missing",
        },
    )
    assert result["code"] == "INVALID_TARGET"
