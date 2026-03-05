"""Geometry measurement helpers."""

from __future__ import annotations

import math
from typing import Any

from klayout_mcp.errors import KLayoutMCPError
from klayout_mcp.models import ShapeRecord

TARGET_COUNTS = {
    "path_width": 1,
    "segment_length": 1,
    "centerline_distance": 2,
    "edge_gap": 2,
    "bend_radius_estimate": 1,
    "overlap": 2,
}


def measure_geometry(
    *,
    runtime: dict[str, Any],
    mode: str,
    target_ids: list[str],
    dbu: float,
) -> dict[str, Any]:
    expected_count = TARGET_COUNTS.get(mode)
    if expected_count is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Unsupported measurement mode",
            {"mode": mode},
        )
    if len(target_ids) != expected_count:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Wrong number of target ids for measurement mode",
            {"mode": mode, "expected": expected_count, "received": len(target_ids)},
        )

    shape_refs = runtime.get("shape_refs", {})
    targets = [_resolve_target(shape_refs, target_id) for target_id in target_ids]

    if mode == "path_width":
        value_dbu = _path_width(targets[0])
        return _response(mode, target_ids, value_dbu, dbu, "stored_path_width")
    if mode == "segment_length":
        value_dbu = _segment_length(targets[0])
        return _response(mode, target_ids, value_dbu, dbu, "polyline_length")
    if mode == "centerline_distance":
        value_dbu = _centerline_distance(targets[0], targets[1])
        return _response(mode, target_ids, value_dbu, dbu, "bbox_center_distance")
    if mode == "edge_gap":
        value_dbu = _edge_gap(targets[0], targets[1])
        return _response(mode, target_ids, value_dbu, dbu, "edge_to_edge_bbox_distance")
    if mode == "bend_radius_estimate":
        value_dbu = _bend_radius_estimate(targets[0])
        return _response(mode, target_ids, value_dbu, dbu, "half_shortest_adjacent_segment")
    if mode == "overlap":
        value_dbu = _overlap_area(targets[0], targets[1])
        return {
            "mode": mode,
            "target_ids": target_ids,
            "value_um": round(value_dbu * (dbu**2), 6),
            "value_dbu": value_dbu,
            "details": {"method": "bbox_overlap_area"},
        }

    raise KLayoutMCPError("INTERNAL_ERROR", "Unhandled measurement mode", {"mode": mode})


def _resolve_target(shape_refs: dict[str, ShapeRecord], target_id: str) -> ShapeRecord:
    target = shape_refs.get(target_id)
    if target is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Requested target id was not found in the session",
            {"target_id": target_id},
        )
    return target


def _response(mode: str, target_ids: list[str], value_dbu: int | float, dbu: float, method: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "target_ids": target_ids,
        "value_um": round(float(value_dbu) * dbu, 6),
        "value_dbu": int(round(value_dbu)),
        "details": {"method": method},
    }


def _path_width(target: ShapeRecord) -> int:
    if target.path_width_dbu is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Target does not support path width measurement",
            {"target_id": target.id},
        )
    return target.path_width_dbu


def _segment_length(target: ShapeRecord) -> float:
    if len(target.points_dbu) < 2:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Target does not have enough points for segment length",
            {"target_id": target.id},
        )
    return _polyline_length(target.points_dbu)


def _centerline_distance(first: ShapeRecord, second: ShapeRecord) -> float:
    ax, ay = _bbox_center(first)
    bx, by = _bbox_center(second)
    return math.hypot(ax - bx, ay - by)


def _edge_gap(first: ShapeRecord, second: ShapeRecord) -> float:
    a_left, a_bottom, a_right, a_top = first.bbox_dbu
    b_left, b_bottom, b_right, b_top = second.bbox_dbu
    dx = max(a_left - b_right, b_left - a_right, 0)
    dy = max(a_bottom - b_top, b_bottom - a_top, 0)
    if dx == 0 and dy == 0:
        return 0.0
    return math.hypot(dx, dy)


def _bend_radius_estimate(target: ShapeRecord) -> float:
    if len(target.points_dbu) < 3:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Target does not have enough segments for bend radius estimation",
            {"target_id": target.id},
        )
    segment_lengths = [
        math.hypot(end[0] - start[0], end[1] - start[1])
        for start, end in zip(target.points_dbu, target.points_dbu[1:], strict=False)
    ]
    return min(segment_lengths) / 2.0


def _overlap_area(first: ShapeRecord, second: ShapeRecord) -> int:
    left = max(first.bbox_dbu[0], second.bbox_dbu[0])
    bottom = max(first.bbox_dbu[1], second.bbox_dbu[1])
    right = min(first.bbox_dbu[2], second.bbox_dbu[2])
    top = min(first.bbox_dbu[3], second.bbox_dbu[3])
    if left >= right or bottom >= top:
        return 0
    return int((right - left) * (top - bottom))


def _polyline_length(points: tuple[tuple[int, int], ...]) -> float:
    return sum(
        math.hypot(end[0] - start[0], end[1] - start[1])
        for start, end in zip(points, points[1:], strict=False)
    )


def _bbox_center(target: ShapeRecord) -> tuple[float, float]:
    left, bottom, right, top = target.bbox_dbu
    return ((left + right) / 2.0, (bottom + top) / 2.0)
