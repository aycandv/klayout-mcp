from pathlib import Path

import pytest


@pytest.mark.anyio
async def test_open_layout_returns_session_and_bbox(mcp_client, generated_layout):
    result = await mcp_client.call("open_layout", {"path": str(generated_layout.path)})

    assert result["session_id"].startswith("ses_")
    assert result["selected_top_cell"] == generated_layout.top_cell
    assert result["bbox_um"]["right"] >= generated_layout.expected_bbox_um.right


@pytest.mark.anyio
async def test_close_session_deletes_session_artifacts(mcp_client, generated_layout):
    opened = await mcp_client.call("open_layout", {"path": str(generated_layout.path)})
    artifact_root = Path(opened["artifact_root"])

    result = await mcp_client.call("close_session", {"session_id": opened["session_id"]})

    assert result["session_id"] == opened["session_id"]
    assert result["closed"] is True
    assert result["artifact_dir_deleted"] is True
    assert not artifact_root.exists()
