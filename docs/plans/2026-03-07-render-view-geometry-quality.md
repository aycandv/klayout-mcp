# Render View Geometry Quality Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the existing `render_view` tool produce inspection-quality PNGs for thin and curved geometry without changing the published MCP contract.

**Architecture:** Keep the external `render_view` request and response shape unchanged, but improve two internal behaviors. First, when callers switch to a different `cell` without supplying a new `box`, derive a fresh render box from that cell's geometry plus a deterministic margin instead of reusing the previously persisted top-level box. Second, render through KLayout's higher-quality image path with explicit layer styling for visible filled geometry and deterministic anti-aliased output.

**Tech Stack:** Python, KLayout `db`/`lay`, pytest, Pillow (dev-only test dependency)

---

### Task 1: Add an inspection fixture and failing render-quality tests

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/fixtures/layout_factory.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_render_view.py`

**Step 1: Write the failing test**

Add a fixture that creates a small curved polygon cell inside a much larger top-level layout extent, then add PNG-inspection assertions that fail with the current renderer:

```python
from PIL import Image
import pytest


def _foreground_pixel_ratio(image_path: Path) -> float:
    image = Image.open(image_path).convert("RGB")
    total = image.width * image.height
    foreground = 0
    for red, green, blue in image.getdata():
        if (red, green, blue) != (255, 255, 255):
            foreground += 1
    return foreground / total


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

    assert _foreground_pixel_ratio(Path(result["image"]["path"])) > 0.08
```

Back the session fixture with a curved polygon fixture using `kdb.DPolygon.ellipse` and a large top-level placement:

```python
def build_curve_inspection_fixture(root: Path) -> GeneratedLayoutFixture:
    layout = _new_layout()
    arc = layout.create_cell("ARC")
    wg = layout.layer(*WG_LAYER)
    arc.shapes(wg).insert(kdb.DPolygon.ellipse(kdb.DBox(0.0, 0.0, 10.0, 4.0), 64))

    top = layout.create_cell("TOP")
    top.insert(kdb.DCellInstArray(arc.cell_index(), kdb.DCplxTrans(1.0, 0.0, False, 200.0, 0.0)))
    return _write_fixture(root, "curve_inspection", layout, top, (WG_LAYER,))
```

Add Pillow to the dev extras:

```toml
dev = [
  "pre-commit>=4.2.0,<5",
  "pytest>=9.0.2,<10",
  "pytest-cov>=7.0.0,<8",
  "ruff>=0.15.5,<0.16",
  "Pillow>=11.3.0,<12",
]
```

**Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py -q`

Expected: FAIL because `render_view` reuses the persisted top-level box when `cell` changes and because the current PNG output does not meet the new foreground-density assertion.

**Step 3: Write minimal implementation**

Do not change production code yet. Only add the fixture, dev dependency, and failing tests.

**Step 4: Run test to verify it still fails for the right reason**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py -q`

Expected: FAIL with assertions on `box_um` and/or foreground pixel ratio, not import errors or fixture errors.

**Step 5: Commit**

```bash
git add pyproject.toml tests/fixtures/layout_factory.py tests/conftest.py tests/test_render_view.py
git commit -m "test: add render inspection quality coverage"
```

### Task 2: Auto-fit the render box when the caller switches cells

**Files:**
- Modify: `src/klayout_mcp/bridge/render.py`
- Test: `tests/test_render_view.py`

**Step 1: Write the failing test**

If Task 1 was done correctly, reuse `test_render_view_refits_box_for_requested_cell` as the failing test. Do not add a second overlapping test.

**Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py::test_render_view_refits_box_for_requested_cell -q`

Expected: FAIL because the returned `box_um` still reflects the top-level session view instead of the requested cell geometry.

**Step 3: Write minimal implementation**

Update view-state normalization so a new cell without an explicit box gets a fresh derived box with deterministic padding:

```python
AUTO_FIT_MARGIN_RATIO = 0.05
AUTO_FIT_MIN_MARGIN_UM = 0.5


def update_view_state(
    *,
    layout: kdb.Layout,
    runtime: dict[str, Any],
    box: dict[str, float] | None = None,
    cell: str | None = None,
    layers: list[dict[str, int | str]] | None = None,
) -> dict[str, Any]:
    current = _current_view_state(layout, runtime)
    resolved_cell = _resolve_cell(layout, cell or current["cell"])
    if box is not None:
        next_box = _normalize_box(box)
    elif cell is not None and resolved_cell != current["cell"]:
        next_box = _auto_fit_box(layout, resolved_cell)
    else:
        next_box = _normalize_box(current["box_um"])

    next_view = {
        "cell": resolved_cell,
        "box_um": next_box,
        "layers": _resolve_layers(runtime["layers"], layers or current["layers"]),
    }
    runtime["view"] = next_view
    return next_view


def _auto_fit_box(layout: kdb.Layout, cell_name: str) -> dict[str, float]:
    bbox = _bbox_for_cell(layout, cell_name)
    width = bbox["right"] - bbox["left"]
    height = bbox["top"] - bbox["bottom"]
    margin = max(width, height) * AUTO_FIT_MARGIN_RATIO
    margin = max(margin, AUTO_FIT_MIN_MARGIN_UM)
    return {
        "left": round(bbox["left"] - margin, 6),
        "bottom": round(bbox["bottom"] - margin, 6),
        "right": round(bbox["right"] + margin, 6),
        "top": round(bbox["top"] + margin, 6),
    }
```

Keep the current behavior when the caller supplies `box` explicitly.

**Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py::test_render_view_refits_box_for_requested_cell -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/render.py tests/test_render_view.py
git commit -m "fix: auto-fit render box for requested cells"
```

### Task 3: Render with deterministic high-detail output for thin geometry

**Files:**
- Modify: `src/klayout_mcp/bridge/render.py`
- Test: `tests/test_render_view.py`

**Step 1: Write the failing test**

Reuse `test_render_view_produces_dense_geometry_pixels_for_curve` from Task 1 as the active red test.

**Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py::test_render_view_produces_dense_geometry_pixels_for_curve -q`

Expected: FAIL because the current render path does not yet apply the high-detail image settings.

**Step 3: Write minimal implementation**

Replace the plain `save_image` call with a deterministic helper based on `save_image_with_options`, and make the visible layers opaque and filled for `light` and `dark` styles:

```python
RENDER_OVERSAMPLING = 3
RENDER_LINEWIDTH = 0
RENDER_RESOLUTION = 0


def render_view(...):
    ...
    _apply_style(view, style)
    _apply_layer_visibility(view, view_state["layers"])
    _apply_geometry_friendly_layer_props(view, style)
    target_box = kdb.DBox(
        box_um["left"],
        box_um["bottom"],
        box_um["right"],
        box_um["top"],
    )
    view.save_image_with_options(
        str(output_path),
        width,
        height,
        RENDER_LINEWIDTH,
        RENDER_OVERSAMPLING,
        RENDER_RESOLUTION,
        target_box,
        False,
    )


def _apply_geometry_friendly_layer_props(view: klay.LayoutView, style: str) -> None:
    for layer in view.each_layer():
        if not layer.visible:
            continue
        if style == "light":
            layer.fill_brightness = 0
            layer.transparent = False
            layer.width = 1
        elif style == "dark":
            layer.fill_brightness = 0
            layer.transparent = False
            layer.width = 1
```

Do not add new tool parameters in this task.

**Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py::test_render_view_produces_dense_geometry_pixels_for_curve -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/render.py tests/test_render_view.py
git commit -m "fix: improve render detail for thin geometry"
```

### Task 4: Run focused verification and clean up

**Files:**
- Modify: `tests/test_render_view.py` (only if threshold tuning or helper cleanup is required)

**Step 1: Write the failing test**

No new tests. Use the full render test file as the verification target.

**Step 2: Run test to verify it fails**

No additional red step is needed in this task.

**Step 3: Write minimal implementation**

Refactor only if needed to keep `src/klayout_mcp/bridge/render.py` readable:

```python
def _render_target_box(box_um: dict[str, float]) -> kdb.DBox:
    return kdb.DBox(box_um["left"], box_um["bottom"], box_um["right"], box_um["top"])
```

Do not change behavior in this step unless verification exposed a real regression.

**Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_render_view.py -q`

Expected: PASS

Run: `./.venv/bin/python -m pytest -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/render.py tests/test_render_view.py
git commit -m "test: verify render quality regressions"
```
