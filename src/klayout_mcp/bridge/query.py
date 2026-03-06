"""Bounded region query helpers."""

from __future__ import annotations

import json
from hashlib import sha1
from typing import Any

import klayout.db as kdb

from klayout_mcp.errors import KLayoutMCPError
from klayout_mcp.models import LayerRef, MicronBox, ShapeRecord


VALID_HIERARCHY_MODES = {"top", "recursive", "flattened"}


def query_region(
    *,
    layout: kdb.Layout,
    runtime: dict[str, Any],
    box: dict[str, float],
    cell_name: str | None = None,
    layers: list[dict[str, int | str]] | None = None,
    hierarchy_mode: str = "recursive",
    max_shapes: int = 200,
    max_instances: int = 100,
) -> dict[str, Any]:
    """Collect shapes, texts, and instances overlapping a query box.

    Args:
        layout: Loaded KLayout database.
        runtime: Session runtime state used for stable shape references.
        box: Query box in microns.
        cell_name: Optional cell override.
        layers: Optional layer filter.
        hierarchy_mode: Query traversal mode.
        max_shapes: Maximum number of shapes to return.
        max_instances: Maximum number of instances to return.

    Returns:
        dict[str, Any]: Query payload containing shapes, texts, and instances.

    Raises:
        KLayoutMCPError: If the query parameters are invalid.
    """
    if hierarchy_mode not in VALID_HIERARCHY_MODES:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Unsupported hierarchy mode",
            {"hierarchy_mode": hierarchy_mode},
        )

    query_cell_name = cell_name or runtime["selected_top_cell"]
    query_cell = layout.cell(query_cell_name)
    if query_cell is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Requested cell was not found",
            {"cell": query_cell_name},
        )

    query_box = _dbox_from_input(box)
    layer_indices = _resolve_layer_indices(layout, layers)
    shape_records: list[ShapeRecord] = []
    text_records: list[dict[str, Any]] = []
    dbu = float(layout.dbu)

    for layer_index in layer_indices:
        info = layout.get_info(layer_index)
        layer_ref = LayerRef(layer=info.layer, datatype=info.datatype, name=info.name or None)
        if hierarchy_mode == "top":
            _collect_top_shapes(
                shape_records=shape_records,
                text_records=text_records,
                cell=query_cell,
                layer_index=layer_index,
                layer_ref=layer_ref,
                query_cell_name=query_cell_name,
                query_box=query_box,
                runtime=runtime,
                dbu=dbu,
            )
            continue

        _collect_recursive_shapes(
            shape_records=shape_records,
            text_records=text_records,
            cell=query_cell,
            layer_index=layer_index,
            layer_ref=layer_ref,
            query_cell_name=query_cell_name,
            query_box=query_box,
            runtime=runtime,
            dbu=dbu,
        )

    # Keep response order deterministic so repeated agent calls are stable.
    sorted_shapes = sorted(
        shape_records,
        key=lambda item: (
            item.layer.layer,
            item.layer.datatype,
            item.kind,
            item.bbox_dbu[0],
            item.bbox_dbu[1],
            item.bbox_dbu[2],
            item.bbox_dbu[3],
            item.id,
        ),
    )
    sorted_texts = sorted(
        text_records,
        key=lambda item: (
            item["layer"]["layer"],
            item["layer"]["datatype"],
            item["text"],
            item["bbox_um"]["left"],
            item["bbox_um"]["bottom"],
        ),
    )
    instances = _collect_instances(query_cell, query_box)

    return {
        "box_um": _micron_box(query_box),
        "cell": query_cell_name,
        "hierarchy_mode": hierarchy_mode,
        "summary": {
            "shape_count": len(sorted_shapes),
            "instance_count": len(instances),
            "text_count": len(sorted_texts),
        },
        "shapes": [shape.to_dict() for shape in sorted_shapes[:max_shapes]],
        "instances": instances[:max_instances],
        "texts": sorted_texts,
        "truncation": {
            "shapes_dropped": max(len(sorted_shapes) - max_shapes, 0),
            "instances_dropped": max(len(instances) - max_instances, 0),
            "texts_dropped": 0,
        },
    }


def _collect_top_shapes(
    *,
    shape_records: list[ShapeRecord],
    text_records: list[dict[str, Any]],
    cell: kdb.Cell,
    layer_index: int,
    layer_ref: LayerRef,
    query_cell_name: str,
    query_box: kdb.DBox,
    runtime: dict[str, Any],
    dbu: float,
) -> None:
    """Collect directly overlapping shapes from the query cell only."""
    for shape in cell.shapes(layer_index).each_overlapping(query_box):
        _add_shape_or_text(
            shape=shape,
            transformed_shape=shape,
            shape_records=shape_records,
            text_records=text_records,
            layer_ref=layer_ref,
            query_cell_name=query_cell_name,
            leaf_cell_name=cell.name,
            instance_path=(query_cell_name,),
            runtime=runtime,
            dbu=dbu,
        )


def _collect_recursive_shapes(
    *,
    shape_records: list[ShapeRecord],
    text_records: list[dict[str, Any]],
    cell: kdb.Cell,
    layer_index: int,
    layer_ref: LayerRef,
    query_cell_name: str,
    query_box: kdb.DBox,
    runtime: dict[str, Any],
    dbu: float,
) -> None:
    """Collect overlapping shapes through hierarchical traversal."""
    iterator = cell.begin_shapes_rec_overlapping(layer_index, query_box)
    while not iterator.at_end():
        shape = iterator.shape()
        transformed_shape = _transform_shape(shape, iterator.trans())
        instance_path = [query_cell_name]
        for path_element in iterator.path():
            instance_path.append(path_element.inst().cell.name)
        _add_shape_or_text(
            shape=shape,
            transformed_shape=transformed_shape,
            shape_records=shape_records,
            text_records=text_records,
            layer_ref=layer_ref,
            query_cell_name=query_cell_name,
            leaf_cell_name=iterator.cell().name,
            instance_path=tuple(instance_path),
            runtime=runtime,
            dbu=dbu,
        )
        iterator.next()


def _add_shape_or_text(
    *,
    shape: kdb.Shape,
    transformed_shape: Any,
    shape_records: list[ShapeRecord],
    text_records: list[dict[str, Any]],
    layer_ref: LayerRef,
    query_cell_name: str,
    leaf_cell_name: str,
    instance_path: tuple[str, ...],
    runtime: dict[str, Any],
    dbu: float,
) -> None:
    """Route one queried object into the shape or text result buckets."""
    if shape.is_text():
        text = transformed_shape.text if hasattr(transformed_shape, "text") else transformed_shape
        text_records.append(
            {
                "text": text.string,
                "layer": layer_ref.to_dict(),
                "bbox_um": _micron_box_from_box(text.bbox(), dbu),
            }
        )
        return

    record = _shape_record(
        shape=shape,
        transformed_shape=transformed_shape,
        layer_ref=layer_ref,
        query_cell_name=query_cell_name,
        leaf_cell_name=leaf_cell_name,
        instance_path=instance_path,
        dbu=dbu,
    )
    # Measurements later refer back to shapes by stable IDs from this query pass.
    runtime.setdefault("shape_refs", {})[record.id] = record
    shape_records.append(record)


def _shape_record(
    *,
    shape: kdb.Shape,
    transformed_shape: Any,
    layer_ref: LayerRef,
    query_cell_name: str,
    leaf_cell_name: str,
    instance_path: tuple[str, ...],
    dbu: float,
) -> ShapeRecord:
    """Build a stable shape record from a queried KLayout shape."""
    bbox = transformed_shape.bbox()
    bbox_dbu = (
        int(bbox.left),
        int(bbox.bottom),
        int(bbox.right),
        int(bbox.top),
    )
    kind = _shape_kind(shape)

    points_dbu: tuple[tuple[int, int], ...] = ()
    point_count: int | None = None
    path_width_um: float | None = None
    path_width_dbu: int | None = None

    if shape.is_path():
        path = transformed_shape.path if hasattr(transformed_shape, "path") else transformed_shape
        points = tuple((int(point.x), int(point.y)) for point in path.each_point())
        points_dbu = points
        point_count = len(points)
        path_width_dbu = int(path.width)
        path_width_um = round(path_width_dbu * dbu, 6)
    elif shape.is_polygon():
        polygon = transformed_shape.polygon if hasattr(transformed_shape, "polygon") else transformed_shape
        points = tuple((int(point.x), int(point.y)) for point in polygon.each_point_hull())
        points_dbu = points
        point_count = len(points)
    elif shape.is_box():
        box = transformed_shape.box if hasattr(transformed_shape, "box") else transformed_shape
        points_dbu = (
            (int(box.left), int(box.bottom)),
            (int(box.right), int(box.top)),
        )

    payload = {
        "kind": kind,
        "cell": query_cell_name,
        "leaf_cell": leaf_cell_name,
        "instance_path": list(instance_path),
        "layer": layer_ref.to_dict(),
        "bbox_dbu": list(bbox_dbu),
        "points_dbu": [list(point) for point in points_dbu],
        "path_width_dbu": path_width_dbu,
    }
    shape_id = f"shp_{sha1(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()[:8]}"

    return ShapeRecord(
        id=shape_id,
        kind=kind,
        cell=query_cell_name,
        leaf_cell=leaf_cell_name,
        instance_path=instance_path,
        layer=layer_ref,
        bbox_um=MicronBox(**_micron_box_from_box(bbox, dbu)),
        bbox_dbu=bbox_dbu,
        point_count=point_count,
        path_width_um=path_width_um,
        path_width_dbu=path_width_dbu,
        points_dbu=points_dbu,
    )


def _collect_instances(cell: kdb.Cell, query_box: kdb.DBox) -> list[dict[str, Any]]:
    """Collect top-level child instances overlapping the query box."""
    instances: list[dict[str, Any]] = []
    for index, instance in enumerate(cell.each_overlapping_inst(query_box)):
        transform = instance.dcplx_trans
        instances.append(
            {
                "name": f"{cell.name}:{index}",
                "child_cell": instance.cell.name,
                "bbox_um": _micron_box(instance.dbbox()),
                "transform": {
                    "magnification": float(transform.mag),
                    "rotation": float(transform.angle),
                    "mirror": bool(transform.is_mirror()),
                    "x_um": round(float(transform.disp.x), 6),
                    "y_um": round(float(transform.disp.y), 6),
                },
            }
        )
    return instances


def _resolve_layer_indices(
    layout: kdb.Layout,
    layers: list[dict[str, int | str]] | None,
) -> list[int]:
    """Resolve optional layer filters into KLayout layer indexes."""
    if not layers:
        return sorted(
            list(layout.layer_indices()),
            key=lambda index: (layout.get_info(index).layer, layout.get_info(index).datatype),
        )

    resolved: list[int] = []
    for layer in layers:
        target_layer = int(layer["layer"])
        target_datatype = int(layer["datatype"])
        match = None
        for layer_index in layout.layer_indices():
            info = layout.get_info(layer_index)
            if info.layer == target_layer and info.datatype == target_datatype:
                match = layer_index
                break
        if match is None:
            raise KLayoutMCPError(
                "INVALID_LAYER",
                "Requested layer was not found in the layout",
                {"layer": target_layer, "datatype": target_datatype},
            )
        resolved.append(match)
    return resolved


def _dbox_from_input(box: dict[str, float]) -> kdb.DBox:
    """Validate and convert a micron query box into a KLayout `DBox`."""
    left = float(box["left"])
    bottom = float(box["bottom"])
    right = float(box["right"])
    top = float(box["top"])
    if left >= right or bottom >= top:
        raise KLayoutMCPError(
            "INVALID_BOX",
            "Query box must have positive width and height",
            {"box": box},
        )
    return kdb.DBox(left, bottom, right, top)


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

def _micron_box(box: kdb.DBox) -> dict[str, float]:
    """Convert a `DBox` into rounded micron coordinates."""
    return {
        "left": round(float(box.left), 6),
        "bottom": round(float(box.bottom), 6),
        "right": round(float(box.right), 6),
        "top": round(float(box.top), 6),
    }


def _micron_box_from_box(box: kdb.Box, dbu: float) -> dict[str, float]:
    """Convert a database-unit box into rounded micron coordinates."""
    return {
        "left": round(float(box.left) * dbu, 6),
        "bottom": round(float(box.bottom) * dbu, 6),
        "right": round(float(box.right) * dbu, 6),
        "top": round(float(box.top) * dbu, 6),
    }
