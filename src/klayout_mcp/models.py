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


@dataclass(slots=True, frozen=True)
class LayerRef:
    layer: int
    datatype: int
    name: str | None = None


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
