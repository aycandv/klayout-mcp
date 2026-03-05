"""MCP tool handlers for layout opening and layer inspection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from klayout_mcp.bridge.hierarchy import describe_cell, list_cells
from klayout_mcp.bridge.layout_loader import LayerSummary, load_layout
from klayout_mcp.bridge.measure import measure_geometry
from klayout_mcp.bridge.query import query_region
from klayout_mcp.bridge.render import default_view_state, render_view, update_view_state
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
                "shape_refs": {},
                "view": default_view_state(
                    selected_top_cell=loaded.selected_top_cell,
                    bbox_um=loaded.bbox_um,
                    layers=loaded.layers,
                ),
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
        runtime = self._require_runtime(session_id)
        layers = [self._layer_response(layer) for layer in runtime["layers"]]
        return {"session_id": session_id, "layers": layers}

    def list_cells(self, session_id: str, max_depth: int | None = None) -> dict[str, Any]:
        runtime = self._require_runtime(session_id)
        return {
            "session_id": session_id,
            "cells": list_cells(runtime["layout"], max_depth=max_depth),
        }

    def describe_cell(self, session_id: str, cell: str, depth: int = 1) -> dict[str, Any]:
        runtime = self._require_runtime(session_id)
        result = describe_cell(runtime["layout"], cell, depth=depth)
        result["session_id"] = session_id
        return result

    def query_region(
        self,
        session_id: str,
        box: dict[str, float],
        cell: str | None = None,
        layers: list[dict[str, int | str]] | None = None,
        hierarchy_mode: str = "recursive",
        max_shapes: int = 200,
        max_instances: int = 100,
    ) -> dict[str, Any]:
        runtime = self._require_runtime(session_id)
        result = query_region(
            layout=runtime["layout"],
            runtime=runtime,
            box=box,
            cell_name=cell,
            layers=layers,
            hierarchy_mode=hierarchy_mode,
            max_shapes=max_shapes,
            max_instances=max_instances,
        )
        result["session_id"] = session_id
        return result

    def measure_geometry(
        self,
        session_id: str,
        mode: str,
        target_ids: list[str],
    ) -> dict[str, Any]:
        runtime = self._require_runtime(session_id)
        result = measure_geometry(
            runtime=runtime,
            mode=mode,
            target_ids=target_ids,
            dbu=float(runtime["layout"].dbu),
        )
        result["session_id"] = session_id
        return result

    def set_view(
        self,
        session_id: str,
        box: dict[str, float] | None = None,
        cell: str | None = None,
        layers: list[dict[str, int | str]] | None = None,
    ) -> dict[str, Any]:
        runtime = self._require_runtime(session_id)
        view = update_view_state(
            layout=runtime["layout"],
            runtime=runtime,
            box=box,
            cell=cell,
            layers=layers,
        )
        self.session_store.update_runtime(session_id, {"view": view})
        return {"session_id": session_id, "view": view}

    def render_view(
        self,
        session_id: str,
        box: dict[str, float] | None = None,
        cell: str | None = None,
        layers: list[dict[str, int | str]] | None = None,
        image_size: dict[str, int] | None = None,
        annotations: list[dict[str, Any]] | None = None,
        style: str = "light",
    ) -> dict[str, Any]:
        session, runtime = self._require_session_and_runtime(session_id)
        return render_view(
            session_id=session_id,
            source_path=session.source_path,
            artifact_dir=session.artifact_dir,
            layout=runtime["layout"],
            runtime=runtime,
            box=box,
            cell=cell,
            layers=layers,
            image_size=image_size,
            style=style,
            annotations=annotations,
        )

    def _layer_response(self, layer: LayerSummary) -> dict[str, Any]:
        return layer.to_response()

    def _require_runtime(self, session_id: str) -> dict[str, Any]:
        _, runtime = self._require_session_and_runtime(session_id)
        return runtime

    def _require_session_and_runtime(self, session_id: str) -> tuple[Any, dict[str, Any]]:
        session = self.session_store.get(session_id)
        if session is None:
            error_code = "SESSION_EXPIRED" if self.session_store.was_expired(session_id) else "SESSION_NOT_FOUND"
            raise KLayoutMCPError(
                error_code,
                "Session is not available",
                {"session_id": session_id},
            )
        runtime = self.session_store.get_runtime(session_id)
        if runtime is None:
            raise KLayoutMCPError(
                "INTERNAL_ERROR",
                "Session runtime is unavailable",
                {"session_id": session_id},
            )
        return session, runtime
