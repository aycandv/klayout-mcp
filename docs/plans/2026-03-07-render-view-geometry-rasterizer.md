# Render View Geometry Rasterizer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current `LayoutView`-based `render_view` internals with a deterministic geometry-driven PNG rasterizer that renders actual polygons, boxes, and paths from KLayout DB data while keeping the MCP contract unchanged.

**Architecture:** Keep `render_view` request and response fields exactly as they are today, but stop delegating image generation to `klayout.lay.LayoutView`. Instead, collect visible geometry directly from the selected cell and its hierarchy, convert every drawable shape to polygonal screen-space geometry, and paint it into a Pillow image with deterministic style colors and box-to-pixel mapping.

**Tech Stack:** Python, KLayout `db`, Pillow, pytest

---

### Task 1: Add a failing regression test for bbox-only rendering

**Files:**
- Modify: `tests/fixtures/layout_factory.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_render_view.py`

**Step 1: Write the failing test**

Add a fixture that embeds the real S-bend polygon profile which currently reproduces the bug under `render_view`:

```python
def build_polygon_profile_fixture(root: Path) -> GeneratedLayoutFixture:
    layout = _new_layout()
    top = layout.create_cell("TOP")
    wg = layout.layer(*WG_LAYER)
    points = [
        kdb.DPoint(0.0, -0.225),
        kdb.DPoint(0.0, 0.225),
        ...
        kdb.DPoint(7.725, 7.5),
        ...
    ]
    top.shapes(wg).insert(kdb.DPolygon(points))
    return _write_fixture(root, "polygon_profile", layout, top, (WG_LAYER,))
```

Add a session fixture and a pixel helper:

```python
def _pixel(image_path: Path, x_ratio: float, y_ratio: float) -> tuple[int, int, int]:
    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        return rgb.getpixel((int(rgb.width * x_ratio), int(rgb.height * y_ratio)))
```

Then add a failing test that distinguishes actual device fill from bbox-only output:

```python
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
    assert _pixel(image_path, 0.50, 0.50) != (255, 255, 255)
    assert _pixel(image_path, 0.10, 0.10) == (255, 255, 255)
```

The first assertion fails with the current renderer because the middle of the image stays white while the cell bbox and label are drawn instead.

**Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py::test_render_view_draws_polygon_geometry_not_cell_bbox -q`

Expected: FAIL because the current `LayoutView` render path shows bbox-only output for this polygon fixture.

**Step 3: Write minimal implementation**

Do not touch production code yet. Only add the fixture, session fixture, and failing test.

**Step 4: Run test to verify it still fails for the right reason**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py::test_render_view_draws_polygon_geometry_not_cell_bbox -q`

Expected: FAIL on the center-pixel assertion, not on fixture or import errors.

**Step 5: Commit**

```bash
git add tests/fixtures/layout_factory.py tests/conftest.py tests/test_render_view.py
git commit -m "test: add render regression for polygon geometry"
```

### Task 2: Replace `LayoutView` rendering with a direct geometry rasterizer

**Files:**
- Modify: `src/klayout_mcp/bridge/render.py`
- Test: `tests/test_render_view.py`

**Step 1: Write the failing test**

Reuse `test_render_view_draws_polygon_geometry_not_cell_bbox` as the active red test.

**Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py::test_render_view_draws_polygon_geometry_not_cell_bbox -q`

Expected: FAIL with the center-pixel assertion.

**Step 3: Write minimal implementation**

Remove the `LayoutView` dependency from the render path and rasterize shapes directly:

```python
from PIL import Image, ImageDraw


def render_view(...):
    ...
    image = Image.new("RGB", (width, height), _background_color(style))
    draw = ImageDraw.Draw(image)
    box_um = view_state["box_um"]
    dbu = float(layout.dbu)
    layer_indices = _resolve_layer_indices(layout, view_state["layers"])
    render_cell = _require_render_cell(layout, view_state["cell"])

    for polygon in _iter_render_polygons(
        cell=render_cell,
        layer_indices=layer_indices,
        query_box=_dbox_from_box_um(box_um),
    ):
        draw.polygon(_project_polygon(polygon, box_um, width, height), fill=_shape_color(style))

    image.save(output_path)
```

Implement helpers for:
- resolving the selected cell
- resolving selected layers back to layout layer indexes
- iterating overlapping shapes recursively with `begin_shapes_rec_overlapping`
- converting boxes and polygons directly to hull point lists
- converting paths with `path.polygon()` or `path.simple_polygon()`
- projecting micron coordinates into pixel coordinates with y-axis inversion

Do not add anti-aliasing, annotations, or text rendering in this task. The goal is correct geometry first.

**Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py::test_render_view_draws_polygon_geometry_not_cell_bbox -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/render.py tests/test_render_view.py
git commit -m "fix: rasterize render geometry directly"
```

### Task 3: Restore existing render behaviors on the new rasterizer

**Files:**
- Modify: `src/klayout_mcp/bridge/render.py`
- Test: `tests/test_render_view.py`

**Step 1: Write the failing test**

Use the existing render tests as the regression suite:
- `test_render_view_writes_png`
- `test_set_view_updates_session_defaults`
- `test_render_view_refits_box_for_requested_cell`
- `test_render_view_produces_dense_geometry_pixels_for_curve`

If needed, add one test for `dark` style background color:

```python
@pytest.mark.anyio
async def test_render_view_dark_style_uses_dark_background(
    mcp_client,
    opened_polygon_profile_session,
):
    result = await mcp_client.call(
        "render_view",
        {
            "session_id": opened_polygon_profile_session,
            "cell": "TOP",
            "image_size": {"width": 400, "height": 200},
            "style": "dark",
        },
    )

    assert _pixel(Path(result["image"]["path"]), 0.05, 0.05) == (0, 0, 0)
```

**Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py -q`

Expected: FAIL if the new rasterizer has not yet matched the style behavior of the old API.

**Step 3: Write minimal implementation**

Add style helpers only:

```python
def _background_color(style: str) -> tuple[int, int, int]:
    if style in {"dark", "mask"}:
        return (0, 0, 0)
    return (255, 255, 255)


def _shape_color(style: str) -> tuple[int, int, int]:
    if style == "mask":
        return (255, 255, 255)
    return (0, 0, 0) if style == "light" else (255, 255, 255)
```

Keep `mask` as monochrome white-on-black geometry.

**Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/render.py tests/test_render_view.py
git commit -m "fix: preserve render styles on rasterizer"
```

### Task 4: Run full verification and validate against the real GDS

**Files:**
- Modify: `src/klayout_mcp/bridge/render.py` (only if verification exposes a real bug)

**Step 1: Write the failing test**

No new unit tests. Use the full suite plus one manual real-GDS verification.

**Step 2: Run test to verify it fails**

No additional red step.

**Step 3: Write minimal implementation**

Only make changes if verification surfaces a regression.

**Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest -q`

Expected: PASS

Run a manual end-to-end render on `/Users/avit/individual/klayout-mcp/fabtol-10-90-2x4-seed-11.gds` and verify a focused S-bend or coupler cell now shows the actual device profile, not a cell bbox.

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/render.py tests/test_render_view.py
git commit -m "test: verify direct geometry rendering"
```
