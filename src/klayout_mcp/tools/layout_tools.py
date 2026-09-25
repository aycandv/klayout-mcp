"""MCP tool handlers for layout sessions.

Each public method's docstring is published to MCP clients as the tool description, so it is
written for the calling agent: what the tool does, when to use it, and what each argument means.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from klayout_mcp.bridge.analyze import analyze_waveguide
from klayout_mcp.bridge.drc import extract_markers, run_drc_script
from klayout_mcp.bridge.hierarchy import describe_cell, list_cells
from klayout_mcp.bridge.layout_loader import load_layout
from klayout_mcp.bridge.measure import measure_geometry
from klayout_mcp.bridge.query import query_region
from klayout_mcp.bridge.render import default_view_state, render_view, update_view_state
from klayout_mcp.config import Settings
from klayout_mcp.errors import KLayoutMCPError
from klayout_mcp.models import SessionRecord, SessionRuntime
from klayout_mcp.session_store import SessionStore


@dataclass(slots=True)
class LayoutTools:
    """Stateful MCP tool handlers bound to one settings and session store pair."""

    settings: Settings
    session_store: SessionStore

    def open_layout(
        self,
        path: str,
        top_cell: str | None = None,
        format: str | None = None,
    ) -> dict[str, Any]:
        """Open a GDS or OASIS layout read-only and start a session.

        Call this first. The returned `session_id` is required by every other tool. Sessions
        expire after a period of inactivity; call `close_session` when finished.

        Args:
            path: Absolute path to a `.gds` or `.oas` file.
            top_cell: Top cell to use by default. Defaults to the alphabetically first top cell.
            format: Explicit format (`gds` or `oas`) when the file extension is ambiguous.
        """
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
            runtime=SessionRuntime(
                layout=loaded.layout,
                layers=loaded.layers,
                selected_top_cell=loaded.selected_top_cell,
                top_cells=loaded.top_cells,
                view=default_view_state(
                    selected_top_cell=loaded.selected_top_cell,
                    bbox_um=loaded.bbox_um,
                    layers=loaded.layers,
                ),
            ),
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
        """Close a session and delete its artifact directory (renders, DRC output).

        Args:
            session_id: Session returned by `open_layout`.
        """
        return self.session_store.close(session_id)

    def list_layers(self, session_id: str) -> dict[str, Any]:
        """List every layer in the layout with its layer/datatype, name, and shape count.

        Use the returned `{layer, datatype}` pairs as layer filters in other tools.

        Args:
            session_id: Session returned by `open_layout`.
        """
        runtime = self._require_runtime(session_id)
        return {
            "session_id": session_id,
            "layers": [layer.to_response() for layer in runtime.layers],
        }

    def list_cells(self, session_id: str, max_depth: int | None = None) -> dict[str, Any]:
        """List cells in the layout hierarchy, sorted by name.

        Each entry has the cell bounding box in microns, whether it is a top cell, its direct
        child instance count, and its direct shape count.

        Args:
            session_id: Session returned by `open_layout`.
            max_depth: Only include cells within this many levels of a top cell (0 = top cells
                only, 1 = top cells and their direct children). Omit to list every cell.
        """
        runtime = self._require_runtime(session_id)
        return {
            "session_id": session_id,
            "cells": list_cells(runtime.layout, max_depth=max_depth),
        }

    def describe_cell(self, session_id: str, cell: str, depth: int = 1) -> dict[str, Any]:
        """Describe one cell: bounding box, child instances, text labels, and shapes per layer.

        Args:
            session_id: Session returned by `open_layout`.
            cell: Name of the cell to describe.
            depth: How many levels of child instances to expand (0 = none).
        """
        runtime = self._require_runtime(session_id)
        result = describe_cell(runtime.layout, cell, depth=depth)
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
        max_texts: int = 200,
    ) -> dict[str, Any]:
        """Return shapes, text labels, and child instances overlapping a box.

        Each returned shape has a session-stable `id` (e.g. `shp_1a2b3c4d`). Pass these ids to
        `measure_geometry`, `analyze_waveguide`, or `render_view` annotations. Results are
        sorted deterministically; `truncation` reports how many items the limits dropped.

        Args:
            session_id: Session returned by `open_layout`.
            box: Query window in microns: `{"left", "bottom", "right", "top"}`.
            cell: Cell to query. Defaults to the session's selected top cell.
            layers: Optional `[{"layer": int, "datatype": int}]` filter. Defaults to all layers.
            hierarchy_mode: `top` for shapes placed directly in the cell, or `recursive` /
                `flattened` to include shapes from child cells transformed into the cell's
                coordinates.
            max_shapes: Maximum number of shapes to return.
            max_instances: Maximum number of child instances to return.
            max_texts: Maximum number of text labels to return.
        """
        runtime = self._require_runtime(session_id)
        result = query_region(
            layout=runtime.layout,
            runtime=runtime,
            box=box,
            cell_name=cell,
            layers=layers,
            hierarchy_mode=hierarchy_mode,
            max_shapes=max_shapes,
            max_instances=max_instances,
            max_texts=max_texts,
        )
        result["session_id"] = session_id
        return result

    def measure_geometry(
        self,
        session_id: str,
        mode: str,
        target_ids: list[str],
    ) -> dict[str, Any]:
        """Measure a value from shapes previously returned by `query_region`.

        Modes and the number of `target_ids` they take:
        `path_width` (1), `segment_length` (1), `bend_radius_estimate` (1),
        `centerline_distance` (2, bounding-box centers), `edge_gap` (2, bounding-box gap),
        `overlap` (2, bounding-box overlap area). Results are in microns and database units.

        Args:
            session_id: Session returned by `open_layout`.
            mode: Measurement mode (see above).
            target_ids: Shape ids from `query_region`.
        """
        runtime = self._require_runtime(session_id)
        result = measure_geometry(
            runtime=runtime,
            mode=mode,
            target_ids=target_ids,
            dbu=float(runtime.layout.dbu),
        )
        result["session_id"] = session_id
        return result

    def analyze_waveguide(self, session_id: str, target_id: str) -> dict[str, Any]:
        """Analyze a path shape as a waveguide: width, length, orientation, and bend estimate.

        Args:
            session_id: Session returned by `open_layout`.
            target_id: Id of a `path` shape returned by `query_region`.
        """
        runtime = self._require_runtime(session_id)
        result = analyze_waveguide(
            runtime=runtime,
            target_id=target_id,
            dbu=float(runtime.layout.dbu),
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
        """Set the session's default render view used by later `render_view` calls.

        Omitted arguments keep their current value. Changing `cell` without a `box`
        auto-fits the view to that cell.

        Args:
            session_id: Session returned by `open_layout`.
            box: View window in microns: `{"left", "bottom", "right", "top"}`.
            cell: Cell to render.
            layers: Visible layers as `[{"layer": int, "datatype": int}]`.
        """
        runtime = self._require_runtime(session_id)
        view = update_view_state(
            layout=runtime.layout,
            runtime=runtime,
            box=box,
            cell=cell,
            layers=layers,
        )
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
        """Render layout geometry to a PNG and return its absolute path.

        Arguments given here also update the session's default view (see `set_view`).

        Args:
            session_id: Session returned by `open_layout`.
            box: View window in microns. Defaults to the current view.
            cell: Cell to render. Defaults to the current view's cell.
            layers: Visible layers as `[{"layer": int, "datatype": int}]`.
            image_size: Output size in pixels: `{"width": int, "height": int}`
                (default 1200x800).
            annotations: Overlays such as
                `[{"kind": "shape_outline", "target_ids": ["shp_..."], "color": "#ff3b30"}]`.
                Targets must come from `query_region` on the rendered cell.
            style: `light`, `dark`, or `mask`.
        """
        session, runtime = self._require_session_and_runtime(session_id)
        return render_view(
            session_id=session_id,
            source_path=session.source_path,
            artifact_dir=session.artifact_dir,
            layout=runtime.layout,
            runtime=runtime,
            box=box,
            cell=cell,
            layers=layers,
            image_size=image_size,
            style=style,
            annotations=annotations,
        )

    def run_drc_script(
        self,
        session_id: str,
        script_path: str,
        script_type: str = "ruby",
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Run a KLayout DRC deck in batch mode against the session layout.

        The deck receives `$input_path` and `$report_path` variables and must write its
        report to `$report_path`. Returns a `run_id` and marker counts per rule; pass the
        `run_id` to `extract_markers` for marker locations. Requires the `klayout` executable
        (on PATH or via `KLAYOUT_BIN`).

        Args:
            session_id: Session returned by `open_layout`.
            script_path: Absolute path to the DRC deck.
            script_type: Deck language. Only `ruby` is supported.
            params: Extra variables passed to the deck with `-rd name=value`.
        """
        session, runtime = self._require_session_and_runtime(session_id)
        return run_drc_script(
            session_id=session_id,
            settings=self.settings,
            session=session,
            runtime=runtime,
            script_path=script_path,
            script_type=script_type,
            params=params,
        )

    def extract_markers(
        self,
        session_id: str,
        run_id: str,
        include_crops: bool = False,
        crop_size_um: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Return the violation markers from a `run_drc_script` run.

        Args:
            session_id: Session returned by `open_layout`.
            run_id: Run id returned by `run_drc_script`.
            include_crops: Also render a PNG crop around each marker.
            crop_size_um: Crop window size in microns: `{"x": float, "y": float}`
                (default 20x20).
        """
        session, runtime = self._require_session_and_runtime(session_id)
        return extract_markers(
            session_id=session_id,
            session=session,
            runtime=runtime,
            run_id=run_id,
            include_crops=include_crops,
            crop_size_um=crop_size_um,
        )

    def _require_runtime(self, session_id: str) -> SessionRuntime:
        """Return runtime state for an active session."""
        _, runtime = self._require_session_and_runtime(session_id)
        return runtime

    def _require_session_and_runtime(
        self,
        session_id: str,
    ) -> tuple[SessionRecord, SessionRuntime]:
        """Return both session metadata and runtime state for an active session."""
        session = self.session_store.get(session_id)
        if session is None:
            expired = self.session_store.was_expired(session_id)
            raise KLayoutMCPError(
                "SESSION_EXPIRED" if expired else "SESSION_NOT_FOUND",
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
