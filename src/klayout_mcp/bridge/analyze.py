"""Waveguide analysis helpers built on cached query targets."""

from __future__ import annotations

from typing import Any

from klayout_mcp.bridge.geometry import bend_radius_estimate, polyline_length
from klayout_mcp.bridge.measure import resolve_target
from klayout_mcp.errors import KLayoutMCPError
from klayout_mcp.models import SessionRuntime, ShapeRecord


def analyze_waveguide(*, runtime: SessionRuntime, target_id: str, dbu: float) -> dict[str, Any]:
    """Analyze one cached waveguide target and return richer path metrics.

    Args:
        runtime: Session runtime state containing cached `ShapeRecord` objects.
        target_id: Shape ID previously returned by `query_region`.
        dbu: Layout database unit size in microns.

    Returns:
        dict[str, Any]: Analysis payload for the requested path target.

    Raises:
        KLayoutMCPError: If the target is missing or is not a supported path.
    """
    target = resolve_target(runtime, target_id)
    if target.kind != "path":
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Waveguide analysis currently supports path targets only",
            {"target_id": target_id, "kind": target.kind},
        )

    center_x, center_y = _bbox_center_um(target)
    segment_length_dbu = polyline_length(target.points_dbu)
    bend_radius_dbu = bend_radius_estimate(target.points_dbu)
    orientation = _orientation(target.points_dbu)

    return {
        "target_id": target.id,
        "kind": target.kind,
        "cell": target.cell,
        "layer": target.layer.to_dict(),
        "bbox_um": target.bbox_um.to_dict(),
        "center_um": {"x": round(center_x, 6), "y": round(center_y, 6)},
        "path_width_um": target.path_width_um,
        "segment_length_um": round(segment_length_dbu * dbu, 6),
        "bend_radius_estimate_um": None if bend_radius_dbu is None else round(bend_radius_dbu * dbu, 6),
        "orientation": orientation,
        "is_path": True,
        "is_axis_aligned": _is_axis_aligned(target.points_dbu),
        "analysis_warnings": [],
    }


def _bbox_center_um(target: ShapeRecord) -> tuple[float, float]:
    """Return the shape bounding-box center in microns."""
    bbox = target.bbox_um
    return ((bbox.left + bbox.right) / 2.0, (bbox.bottom + bbox.top) / 2.0)


def _orientation(points: tuple[tuple[int, int], ...]) -> str:
    """Classify the dominant path orientation for v1 waveguide analysis."""
    if len(points) < 2:
        return "unknown"

    deltas = [
        (end[0] - start[0], end[1] - start[1])
        for start, end in zip(points, points[1:], strict=False)
    ]
    if all(delta_y == 0 for _, delta_y in deltas):
        return "horizontal"
    if all(delta_x == 0 for delta_x, _ in deltas):
        return "vertical"
    return "mixed"


def _is_axis_aligned(points: tuple[tuple[int, int], ...]) -> bool:
    """Return whether every segment is horizontal or vertical."""
    if len(points) < 2:
        return False

    return all(delta_x == 0 or delta_y == 0 for delta_x, delta_y in (
        (end[0] - start[0], end[1] - start[1])
        for start, end in zip(points, points[1:], strict=False)
    ))
