"""Geometry and layer helpers shared across bridge modules."""

from __future__ import annotations

import math
from typing import Any

import klayout.db as kdb

from klayout_mcp.errors import KLayoutMCPError


def micron_box(box: kdb.DBox) -> dict[str, float]:
    """Convert a KLayout `DBox` into rounded micron coordinates."""
    return {
        "left": round(float(box.left), 6),
        "bottom": round(float(box.bottom), 6),
        "right": round(float(box.right), 6),
        "top": round(float(box.top), 6),
    }


def micron_box_from_box(box: kdb.Box, dbu: float) -> dict[str, float]:
    """Convert a database-unit box into rounded micron coordinates."""
    return {
        "left": round(float(box.left) * dbu, 6),
        "bottom": round(float(box.bottom) * dbu, 6),
        "right": round(float(box.right) * dbu, 6),
        "top": round(float(box.top) * dbu, 6),
    }


def dbu_box(box: kdb.Box) -> dict[str, int]:
    """Convert a KLayout `Box` into integer database-unit coordinates."""
    return {
        "left": int(box.left),
        "bottom": int(box.bottom),
        "right": int(box.right),
        "top": int(box.top),
    }


def shape_kind(shape: kdb.Shape) -> str:
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


def transform_shape(shape: kdb.Shape, transform: Any) -> Any:
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


def resolve_layer_indices(
    layout: kdb.Layout,
    layers: list[dict[str, Any]] | None,
) -> list[int]:
    """Resolve optional layer filters into sorted, de-duplicated layer indexes.

    Args:
        layout: Loaded KLayout database.
        layers: Optional `{layer, datatype}` filters; `None` or empty selects every layer.

    Returns:
        list[int]: Layer indexes sorted by `(layer, datatype)`.

    Raises:
        KLayoutMCPError: If a requested layer does not exist in the layout.
    """
    by_key = {
        (layout.get_info(index).layer, layout.get_info(index).datatype): index
        for index in layout.layer_indices()
    }
    if not layers:
        return [by_key[key] for key in sorted(by_key)]

    requested: set[tuple[int, int]] = set()
    for layer in layers:
        key = (int(layer["layer"]), int(layer["datatype"]))
        if key not in by_key:
            raise KLayoutMCPError(
                "INVALID_LAYER",
                "Requested layer was not found in the layout",
                {"layer": key[0], "datatype": key[1]},
            )
        requested.add(key)
    return [by_key[key] for key in sorted(requested)]


def segment_lengths(points: tuple[tuple[int, int], ...]) -> list[float]:
    """Return the length of each consecutive polyline segment in database units."""
    return [
        math.hypot(end[0] - start[0], end[1] - start[1])
        for start, end in zip(points, points[1:], strict=False)
    ]


def polyline_length(points: tuple[tuple[int, int], ...]) -> float:
    """Return the total length of a polyline in database units."""
    return sum(segment_lengths(points))


def bend_radius_estimate(points: tuple[tuple[int, int], ...]) -> float | None:
    """Estimate bend radius as half the shortest segment, or `None` without a bend."""
    if len(points) < 3:
        return None
    return min(segment_lengths(points)) / 2.0
