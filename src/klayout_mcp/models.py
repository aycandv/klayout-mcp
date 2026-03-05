"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(slots=True, frozen=True)
class MicronBox:
    left: float
    bottom: float
    right: float
    top: float

    def to_dict(self) -> dict[str, float]:
        return {
            "left": self.left,
            "bottom": self.bottom,
            "right": self.right,
            "top": self.top,
        }


@dataclass(slots=True, frozen=True)
class LayerRef:
    layer: int
    datatype: int
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "layer": self.layer,
            "datatype": self.datatype,
        }
        if self.name:
            result["name"] = self.name
        return result


@dataclass(slots=True, frozen=True)
class ShapeRecord:
    id: str
    kind: str
    cell: str
    leaf_cell: str
    instance_path: tuple[str, ...]
    layer: LayerRef
    bbox_um: MicronBox
    bbox_dbu: tuple[int, int, int, int]
    point_count: int | None = None
    path_width_um: float | None = None
    path_width_dbu: int | None = None
    points_dbu: tuple[tuple[int, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "cell": self.cell,
            "instance_path": list(self.instance_path),
            "layer": self.layer.to_dict(),
            "bbox_um": self.bbox_um.to_dict(),
        }
        if self.point_count is not None:
            result["point_count"] = self.point_count
        if self.path_width_um is not None:
            result["path_width_um"] = self.path_width_um
        return result


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    artifact_dir: Path
    source_path: Path
    layout_format: str
    top_cell: str
    dbu: float
    created_at: datetime
    last_accessed_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self, *, when: datetime | None = None) -> None:
        self.last_accessed_at = when or utc_now()

    def to_json(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "artifact_dir": str(self.artifact_dir),
            "source": {
                "path": str(self.source_path),
                "format": self.layout_format,
            },
            "top_cell": self.top_cell,
            "dbu": self.dbu,
            "created_at": self.created_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat(),
            "metadata": self.metadata,
        }
