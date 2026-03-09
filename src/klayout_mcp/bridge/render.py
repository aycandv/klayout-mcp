"""Deterministic geometry-driven rendering helpers."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

import klayout.db as kdb
from PIL import Image, ImageDraw

from klayout_mcp.bridge.layout_loader import LayerSummary
from klayout_mcp.errors import KLayoutMCPError

ALLOWED_STYLES = {"light", "dark", "mask"}
DEFAULT_IMAGE_SIZE = {"width": 1200, "height": 800}
AUTO_FIT_MARGIN_RATIO = 0.05
AUTO_FIT_MIN_MARGIN_UM = 0.5


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
    resolved_cell = _resolve_cell(layout, cell or current["cell"])
    next_box = _resolve_view_box(
        layout=layout,
        current_view=current,
        requested_box=box,
        requested_cell=cell,
        resolved_cell=resolved_cell,
    )
    next_view = {
        "cell": resolved_cell,
        "box_um": next_box,
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
    del source_path, annotations

    if style not in ALLOWED_STYLES:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Unsupported render style",
            {"style": style},
        )

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

    image = _render_geometry_image(
        layout=layout,
        cell_name=view_state["cell"],
        box_um=view_state["box_um"],
        selected_layers=view_state["layers"],
        width=width,
        height=height,
        style=style,
    )
    image.save(output_path)

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


def _render_geometry_image(
    *,
    layout: kdb.Layout,
    cell_name: str,
    box_um: dict[str, float],
    selected_layers: list[dict[str, Any]],
    width: int,
    height: int,
    style: str,
) -> Image.Image:
    """Rasterize layout geometry directly into a Pillow image."""
    background = _background_color(style)
    shape_color = _shape_color(style)
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    render_cell = _resolve_cell(layout, cell_name)
    query_box = _render_target_box(box_um)
    dbu = float(layout.dbu)

    for hull, holes in _iter_render_polygons(
        layout=layout,
        cell=layout.cell(render_cell),
        query_box=query_box,
        selected_layers=selected_layers,
        dbu=dbu,
    ):
        projected_hull = _project_points(hull, box_um, width, height)
        if len(projected_hull) < 3:
            continue
        draw.polygon(projected_hull, fill=shape_color)
        for hole in holes:
            projected_hole = _project_points(hole, box_um, width, height)
            if len(projected_hole) < 3:
                continue
            draw.polygon(projected_hole, fill=background)
    return image


def _iter_render_polygons(
    *,
    layout: kdb.Layout,
    cell: kdb.Cell | None,
    query_box: kdb.DBox,
    selected_layers: list[dict[str, Any]],
    dbu: float,
) -> list[tuple[list[tuple[float, float]], list[list[tuple[float, float]]]]]:
    """Collect renderable polygons from the selected cell hierarchy."""
    if cell is None:
        return []

    polygons: list[
        tuple[
            tuple[int, int, str, int, int, int, int],
            list[tuple[float, float]],
            list[list[tuple[float, float]]],
        ]
    ] = []

    for layer_index in _resolve_layer_indices(layout, selected_layers):
        info = layout.get_info(layer_index)
        iterator = cell.begin_shapes_rec_overlapping(layer_index, query_box)
        while not iterator.at_end():
            shape = iterator.shape()
            transformed_shape = _transform_shape(shape, iterator.trans())
            polygon_data = _shape_to_polygon_data(shape, transformed_shape, dbu)
            if polygon_data is not None:
                bbox = transformed_shape.bbox()
                polygons.append(
                    (
                        (
                            info.layer,
                            info.datatype,
                            _shape_kind(shape),
                            int(bbox.left),
                            int(bbox.bottom),
                            int(bbox.right),
                            int(bbox.top),
                        ),
                        polygon_data[0],
                        polygon_data[1],
                    )
                )
            iterator.next()

    polygons.sort(key=lambda item: item[0])
    return [(hull, holes) for _, hull, holes in polygons]


def _shape_to_polygon_data(
    shape: kdb.Shape,
    transformed_shape: Any,
    dbu: float,
) -> tuple[list[tuple[float, float]], list[list[tuple[float, float]]]] | None:
    """Convert one KLayout shape into a hull plus optional hole polygons."""
    if shape.is_text():
        return None
    if shape.is_box():
        box = transformed_shape.box if hasattr(transformed_shape, "box") else transformed_shape
        return (_box_points_um(box, dbu), [])
    if shape.is_path():
        path = transformed_shape.path if hasattr(transformed_shape, "path") else transformed_shape
        polygon = path.simple_polygon()
        return (_simple_polygon_points_um(polygon, dbu), [])
    if shape.is_polygon():
        polygon = transformed_shape.polygon if hasattr(transformed_shape, "polygon") else transformed_shape
        hull = _polygon_points_um(polygon.each_point_hull(), dbu)
        holes = [_polygon_points_um(polygon.each_point_hole(index), dbu) for index in range(polygon.holes())]
        return (hull, holes)
    return None


def _box_points_um(box: kdb.Box, dbu: float) -> list[tuple[float, float]]:
    """Return the four box corners in micron coordinates."""
    return [
        (float(box.left) * dbu, float(box.bottom) * dbu),
        (float(box.right) * dbu, float(box.bottom) * dbu),
        (float(box.right) * dbu, float(box.top) * dbu),
        (float(box.left) * dbu, float(box.top) * dbu),
    ]


def _simple_polygon_points_um(
    polygon: kdb.SimplePolygon | kdb.DSimplePolygon,
    dbu: float,
) -> list[tuple[float, float]]:
    """Return one simple polygon point list in micron coordinates."""
    return [(float(point.x) * dbu, float(point.y) * dbu) for point in polygon.each_point()]


def _polygon_points_um(points: Any, dbu: float) -> list[tuple[float, float]]:
    """Convert a KLayout point iterator into micron coordinates."""
    return [(float(point.x) * dbu, float(point.y) * dbu) for point in points]


def _project_points(
    points_um: list[tuple[float, float]],
    box_um: dict[str, float],
    width: int,
    height: int,
) -> list[tuple[float, float]]:
    """Project micron coordinates into image pixel coordinates."""
    left = box_um["left"]
    bottom = box_um["bottom"]
    span_x = box_um["right"] - left
    span_y = box_um["top"] - bottom
    projected: list[tuple[float, float]] = []
    for x_um, y_um in points_um:
        px = ((x_um - left) / span_x) * (width - 1)
        py = (height - 1) - (((y_um - bottom) / span_y) * (height - 1))
        projected.append((px, py))
    return projected


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


def _resolve_view_box(
    *,
    layout: kdb.Layout,
    current_view: dict[str, Any],
    requested_box: dict[str, float] | None,
    requested_cell: str | None,
    resolved_cell: str,
) -> dict[str, float]:
    """Resolve the next persisted render box for the requested view."""
    if requested_box is not None:
        return _normalize_box(requested_box)
    if requested_cell is not None and resolved_cell != current_view["cell"]:
        return _auto_fit_box(layout, resolved_cell)
    return _normalize_box(current_view["box_um"])


def _auto_fit_box(layout: kdb.Layout, cell_name: str) -> dict[str, float]:
    """Return a deterministic padded box around one cell's geometry."""
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


def _resolve_layer_indices(layout: kdb.Layout, selected_layers: list[dict[str, Any]]) -> list[int]:
    """Resolve normalized visible layers back to concrete layout layer indices."""
    requested = {(int(layer["layer"]), int(layer["datatype"])) for layer in selected_layers}
    resolved = [
        layer_index
        for layer_index in layout.layer_indices()
        if (
            layout.get_info(layer_index).layer,
            layout.get_info(layer_index).datatype,
        ) in requested
    ]
    return sorted(
        resolved,
        key=lambda index: (layout.get_info(index).layer, layout.get_info(index).datatype),
    )


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


def _background_color(style: str) -> tuple[int, int, int]:
    """Return the background color for one render style."""
    if style in {"dark", "mask"}:
        return (0, 0, 0)
    return (255, 255, 255)


def _shape_color(style: str) -> tuple[int, int, int]:
    """Return the geometry color for one render style."""
    if style == "light":
        return (0, 0, 0)
    return (255, 255, 255)


def _render_target_box(box_um: dict[str, float]) -> kdb.DBox:
    """Convert a normalized micron box into a KLayout render target box."""
    return kdb.DBox(box_um["left"], box_um["bottom"], box_um["right"], box_um["top"])


def _shape_kind(shape: kdb.Shape) -> str:
    """Return the contract shape kind for a KLayout shape."""
    if shape.is_path():
        return "path"
    if shape.is_box():
        return "box"
    if shape.is_polygon():
        return "polygon"
    if shape.is_text():
        return "text"
    return "shape"


def _transform_shape(shape: kdb.Shape, transform: Any) -> Any:
    """Apply an iterator transform to the current shape payload."""
    if shape.is_path():
        return shape.path.transformed(transform)
    if shape.is_box():
        return shape.box.transformed(transform)
    if shape.is_polygon():
        return shape.polygon.transformed(transform)
    if shape.is_text():
        return shape.text.transformed(transform)
    return shape


def _layer_to_ref(layer: LayerSummary) -> dict[str, Any]:
    """Convert a layer summary into the persisted view-layer form."""
    return layer.to_response()
