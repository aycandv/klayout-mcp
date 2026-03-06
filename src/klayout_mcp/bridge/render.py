"""Deterministic rendering helpers built on KLayout LayoutView."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

import klayout.db as kdb
import klayout.lay as klay

from klayout_mcp.bridge.layout_loader import LayerSummary
from klayout_mcp.errors import KLayoutMCPError

ALLOWED_STYLES = {"light", "dark", "mask"}
DEFAULT_IMAGE_SIZE = {"width": 1200, "height": 800}


def default_view_state(
    *,
    selected_top_cell: str,
    bbox_um: dict[str, float],
    layers: list[LayerSummary],
) -> dict[str, Any]:
    """Build the default persisted view for a newly opened session.

    Args:
        selected_top_cell: Default cell to render.
        bbox_um: Initial view box in microns.
        layers: Visible layout layers.

    Returns:
        dict[str, Any]: Serializable default view state.
    """
    return {
        "cell": selected_top_cell,
        "box_um": dict(bbox_um),
        "layers": [_layer_to_ref(layer) for layer in layers],
    }


def update_view_state(
    *,
    layout: kdb.Layout,
    runtime: dict[str, Any],
    box: dict[str, float] | None = None,
    cell: str | None = None,
    layers: list[dict[str, int | str]] | None = None,
) -> dict[str, Any]:
    """Validate and persist the session's current render view.

    Args:
        layout: Loaded KLayout database.
        runtime: Session runtime state.
        box: Optional replacement box in microns.
        cell: Optional replacement cell.
        layers: Optional replacement visible layers.

    Returns:
        dict[str, Any]: Updated persisted view state.
    """
    current = _current_view_state(layout, runtime)
    next_view = {
        "cell": _resolve_cell(layout, cell or current["cell"]),
        "box_um": _normalize_box(box or current["box_um"]),
        "layers": _resolve_layers(runtime["layers"], layers or current["layers"]),
    }
    runtime["view"] = next_view
    return next_view


def render_view(
    *,
    session_id: str,
    source_path: Path,
    artifact_dir: Path,
    layout: kdb.Layout,
    runtime: dict[str, Any],
    box: dict[str, float] | None = None,
    cell: str | None = None,
    layers: list[dict[str, int | str]] | None = None,
    image_size: dict[str, int] | None = None,
    style: str = "light",
    annotations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Render the current or requested view state into a deterministic PNG.

    Args:
        session_id: Active session identifier.
        source_path: Absolute layout source path.
        artifact_dir: Session artifact directory.
        layout: Loaded KLayout database.
        runtime: Session runtime state.
        box: Optional replacement view box in microns.
        cell: Optional replacement cell.
        layers: Optional replacement visible layers.
        image_size: Optional output image size.
        style: Render style name.
        annotations: Reserved annotation payload.

    Returns:
        dict[str, Any]: Render metadata and output artifact path.

    Raises:
        KLayoutMCPError: If the view request is invalid.
    """
    del annotations

    if style not in ALLOWED_STYLES:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Unsupported render style",
            {"style": style},
        )

    # Rendering updates the persisted view so later calls inherit the same framing.
    view_state = update_view_state(
        layout=layout,
        runtime=runtime,
        box=box,
        cell=cell,
        layers=layers,
    )
    width, height = _normalize_image_size(image_size)
    render_id = f"rnd_{secrets.token_hex(4)}"
    output_path = artifact_dir / "renders" / f"{render_id}.png"

    view = klay.LayoutView()
    cellview_index = view.load_layout(str(source_path))
    view.add_missing_layers()

    cv = view.cellview(cellview_index)
    render_layout = cv.layout()
    render_cell = render_layout.cell(view_state["cell"])
    if render_cell is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Requested render cell was not found",
            {"cell": view_state["cell"]},
        )

    view.select_cell(cellview_index, render_cell.cell_index())
    _apply_style(view, style)
    _apply_layer_visibility(view, view_state["layers"])
    box_um = view_state["box_um"]
    view.zoom_box(kdb.DBox(box_um["left"], box_um["bottom"], box_um["right"], box_um["top"]))
    view.save_image(str(output_path), width, height)

    return {
        "session_id": session_id,
        "render_id": render_id,
        "box_um": dict(view_state["box_um"]),
        "image": {
            "kind": "render",
            "path": str(output_path.resolve()),
            "media_type": "image/png",
        },
        "width": width,
        "height": height,
        "style": style,
    }


def _current_view_state(layout: kdb.Layout, runtime: dict[str, Any]) -> dict[str, Any]:
    """Return the persisted view state, creating the default when absent."""
    if "view" in runtime:
        return runtime["view"]

    default = default_view_state(
        selected_top_cell=runtime["selected_top_cell"],
        bbox_um=_bbox_for_cell(layout, runtime["selected_top_cell"]),
        layers=runtime["layers"],
    )
    runtime["view"] = default
    return default


def _bbox_for_cell(layout: kdb.Layout, cell_name: str) -> dict[str, float]:
    """Return the rounded micron bounding box for a named cell."""
    cell = layout.cell(cell_name)
    if cell is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Requested cell was not found",
            {"cell": cell_name},
        )
    box = cell.dbbox()
    return {
        "left": round(float(box.left), 6),
        "bottom": round(float(box.bottom), 6),
        "right": round(float(box.right), 6),
        "top": round(float(box.top), 6),
    }


def _resolve_cell(layout: kdb.Layout, cell_name: str) -> str:
    """Validate that a requested render cell exists."""
    if layout.cell(cell_name) is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Requested cell was not found",
            {"cell": cell_name},
        )
    return cell_name


def _resolve_layers(
    available_layers: list[LayerSummary],
    requested_layers: list[dict[str, int | str]],
) -> list[dict[str, Any]]:
    """Resolve requested visible layers against the loaded layer set."""
    available = {
        (layer.layer, layer.datatype): _layer_to_ref(layer)
        for layer in available_layers
    }

    resolved: list[dict[str, Any]] = []
    for layer in requested_layers:
        key = (int(layer["layer"]), int(layer["datatype"]))
        if key not in available:
            raise KLayoutMCPError(
                "INVALID_LAYER",
                "Requested layer was not found in the layout",
                {"layer": key[0], "datatype": key[1]},
            )
        resolved.append(dict(available[key]))
    return resolved


def _normalize_box(box: dict[str, float]) -> dict[str, float]:
    """Validate and round a view box in microns."""
    left = float(box["left"])
    bottom = float(box["bottom"])
    right = float(box["right"])
    top = float(box["top"])
    if left >= right or bottom >= top:
        raise KLayoutMCPError(
            "INVALID_BOX",
            "View box must have positive width and height",
            {"box": box},
        )
    return {
        "left": round(left, 6),
        "bottom": round(bottom, 6),
        "right": round(right, 6),
        "top": round(top, 6),
    }


def _normalize_image_size(image_size: dict[str, int] | None) -> tuple[int, int]:
    """Validate and normalize the requested output image size."""
    if image_size is None:
        return (DEFAULT_IMAGE_SIZE["width"], DEFAULT_IMAGE_SIZE["height"])
    width = int(image_size["width"])
    height = int(image_size["height"])
    if width <= 0 or height <= 0:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Image size must be positive",
            {"image_size": image_size},
        )
    return (width, height)


def _apply_style(view: klay.LayoutView, style: str) -> None:
    """Apply one of the supported deterministic render styles."""
    view.set_config("grid-visible", "false")
    if style == "light":
        view.set_config("background-color", "#ffffff")
        return
    if style == "dark":
        view.set_config("background-color", "#000000")
        return

    view.set_config("background-color", "#000000")
    for layer in view.each_layer():
        layer.fill_color = 0xFFFFFFFF
        layer.frame_color = 0xFFFFFFFF
        layer.transparent = False


def _apply_layer_visibility(view: klay.LayoutView, selected_layers: list[dict[str, Any]]) -> None:
    """Apply layer visibility from the normalized view state."""
    visible = {(int(layer["layer"]), int(layer["datatype"])) for layer in selected_layers}
    for layer in view.each_layer():
        layer.visible = (int(layer.source_layer), int(layer.source_datatype)) in visible


def _layer_to_ref(layer: LayerSummary) -> dict[str, Any]:
    """Convert a layer summary into the persisted view-layer form."""
    return layer.to_response()
