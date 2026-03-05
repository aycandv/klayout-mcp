"""MCP tool handlers for layout opening and layer inspection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from klayout_mcp.bridge.layout_loader import LayerSummary, load_layout
from klayout_mcp.config import Settings
from klayout_mcp.errors import KLayoutMCPError
from klayout_mcp.session_store import SessionStore


@dataclass(slots=True)
class LayoutTools:
    settings: Settings
    session_store: SessionStore

    def open_layout(
        self,
        path: str,
        top_cell: str | None = None,
        format: str | None = None,
    ) -> dict[str, Any]:
        loaded = load_layout(
            path=path,
            settings=self.settings,
            top_cell=top_cell,
            layout_format=format,
        )
        session = self.session_store.create_session(
            source_path=loaded.resolved_path,
            layout_format=loaded.layout_format,
            top_cell=loaded.selected_top_cell,
            dbu=loaded.dbu,
            metadata={
                "sha256": loaded.source_sha256,
                "top_cells": loaded.top_cells,
                "bbox_um": loaded.bbox_um,
                "bbox_dbu": loaded.bbox_dbu,
                "layer_count": len(loaded.layers),
            },
            runtime={
                "layout": loaded.layout,
                "layers": loaded.layers,
                "selected_top_cell": loaded.selected_top_cell,
                "top_cells": loaded.top_cells,
            },
        )
        return {
            "session_id": session.session_id,
            "source": {
                "path": str(loaded.resolved_path),
                "format": loaded.layout_format,
                "sha256": loaded.source_sha256,
            },
            "selected_top_cell": loaded.selected_top_cell,
            "top_cells": loaded.top_cells,
            "dbu": loaded.dbu,
            "bbox_um": loaded.bbox_um,
            "bbox_dbu": loaded.bbox_dbu,
            "layer_count": len(loaded.layers),
            "artifact_root": str(session.artifact_dir),
        }

    def close_session(self, session_id: str) -> dict[str, Any]:
        return self.session_store.close(session_id)

    def list_layers(self, session_id: str) -> dict[str, Any]:
        self._require_session(session_id)
        runtime = self.session_store.get_runtime(session_id)
        if runtime is None:
            raise KLayoutMCPError(
                "INTERNAL_ERROR",
                "Session runtime is unavailable",
                {"session_id": session_id},
            )

        layers = [self._layer_response(layer) for layer in runtime["layers"]]
        return {"session_id": session_id, "layers": layers}

    def _layer_response(self, layer: LayerSummary) -> dict[str, Any]:
        return layer.to_response()

    def _require_session(self, session_id: str) -> None:
        session = self.session_store.get(session_id)
        if session is not None:
            return
        error_code = "SESSION_EXPIRED" if self.session_store.was_expired(session_id) else "SESSION_NOT_FOUND"
        raise KLayoutMCPError(
            error_code,
            "Session is not available",
            {"session_id": session_id},
        )
