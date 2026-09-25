"""Bounded region query helpers."""

from __future__ import annotations

import json
from hashlib import sha1
from typing import Any

import klayout.db as kdb

from klayout_mcp.bridge.geometry import (
    micron_box,
    micron_box_from_box,
    resolve_layer_indices,
    shape_kind,
    transform_shape,
)
from klayout_mcp.errors import KLayoutMCPError
from klayout_mcp.models import LayerRef, MicronBox, SessionRuntime, ShapeRecord


VALID_HIERARCHY_MODES = {"top", "recursive", "flattened"}


def query_region(
    *,
    layout: kdb.Layout,
    runtime: SessionRuntime,
    box: dict[str, float],
    cell_name: str | None = None,
    layers: list[dict[str, int | str]] | None = None,
    hierarchy_mode: str = "recursive",
    max_shapes: int = 200,
    max_instances: int = 100,
    max_texts: int = 200,
) -> dict[str, Any]:
    """Collect shapes, texts, and instances overlapping a query box.

    Args:
        layout: Loaded KLayout database.
        runtime: Session runtime state that caches the returned shapes by ID.
        box: Query box in microns.
        cell_name: Optional cell override.
        layers: Optional layer filter.
        hierarchy_mode: Query traversal mode.
        max_shapes: Maximum number of shapes to return.
        max_instances: Maximum number of instances to return.
        max_texts: Maximum number of text labels to return.

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

    for limit_name, limit_value in (
        ("max_shapes", max_shapes),
        ("max_instances", max_instances),
        ("max_texts", max_texts),
    ):
        if limit_value < 0:
            raise KLayoutMCPError(
                "INVALID_TARGET",
                f"{limit_name} must be zero or greater",
                {limit_name: limit_value},
            )

    query_cell_name = cell_name or runtime.selected_top_cell
    query_cell = layout.cell(query_cell_name)
    if query_cell is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Requested cell was not found",
            {"cell": query_cell_name},
        )

    query_box = _dbox_from_input(box)
    layer_indices = resolve_layer_indices(layout, layers)
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
    returned_shapes = sorted_shapes[:max_shapes]
    # Later tools resolve shapes by the IDs handed out here. Cache only those, so memory
    # tracks what the caller has seen and issued IDs stay valid for the whole session.
    for shape in returned_shapes:
        runtime.remember_shape(shape)
    instances = _collect_instances(query_cell, query_box)

    return {
        "box_um": micron_box(query_box),
        "cell": query_cell_name,
        "hierarchy_mode": hierarchy_mode,
        "summary": {
            "shape_count": len(sorted_shapes),
            "instance_count": len(instances),
            "text_count": len(sorted_texts),
        },
        "shapes": [shape.to_dict() for shape in returned_shapes],
        "instances": instances[:max_instances],
        "texts": sorted_texts[:max_texts],
        "truncation": {
            "shapes_dropped": max(len(sorted_shapes) - max_shapes, 0),
            "instances_dropped": max(len(instances) - max_instances, 0),
            "texts_dropped": max(len(sorted_texts) - max_texts, 0),
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
    dbu: float,
) -> None:
    """Collect overlapping shapes through hierarchical traversal."""
    iterator = cell.begin_shapes_rec_overlapping(layer_index, query_box)
    while not iterator.at_end():
        shape = iterator.shape()
        transformed_shape = transform_shape(shape, iterator.trans())
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
    dbu: float,
) -> None:
    """Route one queried object into the shape or text result buckets."""
    if shape.is_text():
        text = transformed_shape.text if hasattr(transformed_shape, "text") else transformed_shape
        text_records.append(
            {
                "text": text.string,
                "layer": layer_ref.to_dict(),
                "bbox_um": micron_box_from_box(text.bbox(), dbu),
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
    kind = shape_kind(shape)

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
        bbox_um=MicronBox(**micron_box_from_box(bbox, dbu)),
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
                "bbox_um": micron_box(instance.dbbox()),
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
