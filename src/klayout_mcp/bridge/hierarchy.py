"""Hierarchy inspection helpers."""

from __future__ import annotations

from typing import Any

import klayout.db as kdb

from klayout_mcp.bridge.layout_loader import _dbu_box, _micron_box
from klayout_mcp.errors import KLayoutMCPError


def list_cells(layout: kdb.Layout, max_depth: int | None = None) -> list[dict[str, Any]]:
    """Return sorted cell summaries for the loaded layout.

    Args:
        layout: Loaded KLayout database.
        max_depth: Reserved hierarchy depth parameter for contract compatibility.

    Returns:
        list[dict[str, Any]]: Deterministically sorted cell summaries.
    """
    top_names = {cell.name for cell in layout.top_cells()}
    cells = []
    for cell in sorted(layout.each_cell(), key=lambda item: item.name):
        cells.append(
            {
                "name": cell.name,
                "is_top": cell.name in top_names,
                "bbox_um": _micron_box(cell.dbbox()),
                "child_instance_count": sum(1 for _ in cell.each_inst()),
                "shape_count": _shape_count(layout, cell),
            }
        )
    return cells


def describe_cell(layout: kdb.Layout, cell_name: str, depth: int = 1) -> dict[str, Any]:
    """Describe one cell, including instances, labels, and per-layer counts.

    Args:
        layout: Loaded KLayout database.
        cell_name: Name of the cell to inspect.
        depth: Recursive instance depth to include.

    Returns:
        dict[str, Any]: Structured description of the requested cell.

    Raises:
        KLayoutMCPError: If the requested cell does not exist.
    """
    cell = layout.cell(cell_name)
    if cell is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Requested cell was not found",
            {"cell": cell_name},
        )

    return {
        "cell": cell.name,
        "bbox_um": _micron_box(cell.dbbox()),
        "bbox_dbu": _dbu_box(cell.bbox()),
        "instances": _collect_instances(cell, max(depth, 0)),
        "labels": _collect_labels(layout, cell),
        "shape_counts_by_layer": _shape_counts_by_layer(layout, cell),
        "depth_used": max(depth, 0),
    }


def _shape_count(layout: kdb.Layout, cell: kdb.Cell) -> int:
    """Count all shapes present directly on a cell across layout layers."""
    return sum(cell.shapes(layer_index).size() for layer_index in layout.layer_indices())


def _shape_counts_by_layer(layout: kdb.Layout, cell: kdb.Cell) -> list[dict[str, Any]]:
    """Return non-zero direct shape counts grouped by layer."""
    counts: list[dict[str, Any]] = []
    for layer_index in layout.layer_indices():
        shape_count = cell.shapes(layer_index).size()
        if shape_count == 0:
            continue
        info = layout.get_info(layer_index)
        entry: dict[str, Any] = {
            "layer": info.layer,
            "datatype": info.datatype,
            "shape_count": shape_count,
        }
        if info.name:
            entry["name"] = info.name
        counts.append(entry)
    return sorted(counts, key=lambda item: (item["layer"], item["datatype"]))


def _collect_labels(layout: kdb.Layout, cell: kdb.Cell) -> list[dict[str, Any]]:
    """Collect text labels placed directly on a cell."""
    labels: list[dict[str, Any]] = []
    for layer_index in layout.layer_indices():
        info = layout.get_info(layer_index)
        for shape in cell.shapes(layer_index).each():
            if not shape.is_text():
                continue
            text = shape.text
            entry: dict[str, Any] = {
                "text": text.string,
                "bbox_um": _micron_box(shape.dbbox()),
                "position_dbu": {
                    "x": int(text.trans.disp.x),
                    "y": int(text.trans.disp.y),
                },
                "layer": {
                    "layer": info.layer,
                    "datatype": info.datatype,
                },
            }
            if info.name:
                entry["layer"]["name"] = info.name
            labels.append(entry)

    return sorted(labels, key=lambda item: (item["text"], item["position_dbu"]["x"], item["position_dbu"]["y"]))


def _collect_instances(cell: kdb.Cell, depth: int) -> list[dict[str, Any]]:
    """Collect instance metadata recursively up to the requested depth."""
    if depth <= 0:
        return []

    instances: list[dict[str, Any]] = []
    for index, instance in enumerate(cell.each_inst()):
        child_cell = instance.cell
        transform = instance.dcplx_trans
        instances.append(
            {
                "name": f"{cell.name}:{index}",
                "child_cell": child_cell.name,
                "array": {
                    "is_array": instance.is_regular_array(),
                    "na": int(instance.na),
                    "nb": int(instance.nb),
                },
                "transform": {
                    "magnification": float(transform.mag),
                    "rotation": float(transform.angle),
                    "mirror": bool(transform.is_mirror()),
                    "x_um": round(float(transform.disp.x), 6),
                    "y_um": round(float(transform.disp.y), 6),
                },
                "bbox_um": _micron_box(instance.dbbox()),
            }
        )
        if depth > 1:
            instances.extend(_collect_instances(child_cell, depth - 1))

    return instances
