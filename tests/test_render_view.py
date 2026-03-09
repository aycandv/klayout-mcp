from pathlib import Path

import pytest
from PIL import Image


def _foreground_pixel_ratio(image_path: Path) -> float:
    with Image.open(image_path) as image:
        pixels = image.convert("RGB")
        total = pixels.width * pixels.height
        foreground = 0
        for red, green, blue in pixels.getdata():
            if (red, green, blue) != (255, 255, 255):
                foreground += 1
    return foreground / total


def _pixel(image_path: Path, x_ratio: float, y_ratio: float) -> tuple[int, int, int]:
    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        x = int(rgb.width * x_ratio)
        y = int(rgb.height * y_ratio)
        return rgb.getpixel((x, y))


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


@pytest.mark.anyio
async def test_render_view_refits_box_for_requested_cell(
    mcp_client,
    opened_curve_inspection_session,
):
    result = await mcp_client.call(
        "render_view",
        {
            "session_id": opened_curve_inspection_session,
            "cell": "ARC",
            "image_size": {"width": 600, "height": 300},
            "style": "light",
        },
    )

    assert result["box_um"]["right"] < 20.0
    assert result["box_um"]["top"] < 10.0


@pytest.mark.anyio
async def test_render_view_produces_dense_geometry_pixels_for_curve(
    mcp_client,
    opened_curve_inspection_session,
):
    result = await mcp_client.call(
        "render_view",
        {
            "session_id": opened_curve_inspection_session,
            "cell": "ARC",
            "image_size": {"width": 600, "height": 300},
            "style": "light",
        },
    )

    # Keep the threshold above the pre-fix render density (~0.009) while allowing
    # for KLayout's rasterized inspection output on thin curved geometry.
    assert _foreground_pixel_ratio(Path(result["image"]["path"])) > 0.03


@pytest.mark.anyio
async def test_render_view_draws_polygon_geometry_not_cell_bbox(
    mcp_client,
    opened_polygon_profile_session,
):
    result = await mcp_client.call(
        "render_view",
        {
            "session_id": opened_polygon_profile_session,
            "cell": "TOP",
            "image_size": {"width": 1200, "height": 600},
            "style": "light",
        },
    )

    image_path = Path(result["image"]["path"])
    assert _pixel(image_path, 0.70, 0.75) != (255, 255, 255)
    assert _pixel(image_path, 0.10, 0.10) == (255, 255, 255)
