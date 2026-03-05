from pathlib import Path

import pytest


@pytest.mark.anyio
async def test_render_view_writes_png(mcp_client, opened_session):
    result = await mcp_client.call(
        "render_view",
        {
            "session_id": opened_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 50.0, "top": 20.0},
            "image_size": {"width": 800, "height": 600},
            "style": "light",
        },
    )

    image_path = Path(result["image"]["path"])
    assert image_path.exists()
    assert image_path.suffix == ".png"


@pytest.mark.anyio
async def test_set_view_updates_session_defaults(mcp_client, opened_session):
    result = await mcp_client.call(
        "set_view",
        {
            "session_id": opened_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 25.0, "top": 10.0},
        },
    )
    rendered = await mcp_client.call(
        "render_view",
        {
            "session_id": opened_session,
            "image_size": {"width": 320, "height": 200},
            "style": "light",
        },
    )

    assert result["view"]["box_um"]["right"] == 25.0
    assert rendered["box_um"]["right"] == 25.0
