"""Helpers for opening layouts and collecting initial summaries."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import klayout.db as kdb

from klayout_mcp.config import Settings
from klayout_mcp.errors import KLayoutMCPError

SUPPORTED_FORMATS = {
    "gds": "gds",
    "gdsii": "gds",
    "oas": "oas",
    "oasis": "oas",
}


@dataclass(slots=True, frozen=True)
class LayerSummary:
    """Serializable summary of one layout layer."""

    layer: int
    datatype: int
    name: str | None
    visible: bool
    shape_count: int

    def to_response(self) -> dict[str, object]:
        """Return the layer summary in tool-response form."""
        response: dict[str, object] = {
            "layer": self.layer,
            "datatype": self.datatype,
            "visible": self.visible,
            "shape_count": self.shape_count,
        }
        if self.name:
            response["name"] = self.name
        return response


@dataclass(slots=True)
class LoadedLayout:
    """Normalized result of loading a layout file for a new session."""

    layout: kdb.Layout
    resolved_path: Path
    layout_format: str
    source_sha256: str
    top_cells: list[str]
    selected_top_cell: str
    dbu: float
    bbox_um: dict[str, float]
    bbox_dbu: dict[str, int]
    layers: list[LayerSummary]


def load_layout(
    *,
    path: str,
    settings: Settings,
    top_cell: str | None = None,
    layout_format: str | None = None,
) -> LoadedLayout:
    """Load a layout from disk and collect session bootstrap metadata.

    Args:
        path: Absolute path to the layout file.
        settings: Process runtime settings.
        top_cell: Optional top cell override.
        layout_format: Optional explicit format hint.

    Returns:
        LoadedLayout: Normalized layout data used to create a session.

    Raises:
        KLayoutMCPError: If the path, format, or top cell is invalid.
    """
    requested_path = Path(path).expanduser()
    if not requested_path.is_absolute():
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Layout path must be absolute",
            {"path": path},
        )

    resolved_path = requested_path.resolve()
    if not resolved_path.exists():
        raise KLayoutMCPError(
            "FILE_NOT_FOUND",
            "Layout file does not exist",
            {"path": str(resolved_path)},
        )

    normalized_format = _normalize_format(resolved_path, layout_format)
    layout = kdb.Layout()
    layout.read(str(resolved_path))

    top_cells = sorted(cell.name for cell in layout.top_cells())
    if not top_cells:
        raise KLayoutMCPError(
            "TOP_CELL_NOT_FOUND",
            "Layout does not contain any top cells",
            {"path": str(resolved_path)},
        )

    selected_top_cell = top_cell or top_cells[0]
    selected_cell = layout.cell(selected_top_cell)
    if selected_cell is None:
        raise KLayoutMCPError(
            "TOP_CELL_NOT_FOUND",
            "Requested top cell was not found",
            {"top_cell": selected_top_cell},
        )

    return LoadedLayout(
        layout=layout,
        resolved_path=resolved_path,
        layout_format=normalized_format,
        source_sha256=_hash_file(resolved_path),
        top_cells=top_cells,
        selected_top_cell=selected_top_cell,
        dbu=round(layout.dbu, 6),
        bbox_um=_micron_box(selected_cell.dbbox()),
        bbox_dbu=_dbu_box(selected_cell.bbox()),
        layers=_collect_layers(layout),
    )


def _normalize_format(path: Path, layout_format: str | None) -> str:
    """Normalize an explicit or inferred layout format to contract values."""
    if layout_format:
        key = layout_format.strip().lower()
    else:
        key = path.suffix.lstrip(".").lower()

    normalized = SUPPORTED_FORMATS.get(key)
    if normalized is None:
        raise KLayoutMCPError(
            "UNSUPPORTED_FORMAT",
            "Unsupported layout format",
            {"path": str(path), "format": layout_format or key},
        )
    return normalized


def _hash_file(path: Path) -> str:
    """Return the SHA-256 digest for a layout file."""
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_layers(layout: kdb.Layout) -> list[LayerSummary]:
    """Collect sorted layer summaries across all cells in the layout."""
    summaries: list[LayerSummary] = []
    for layer_index in layout.layer_indices():
        info = layout.get_info(layer_index)
        shape_count = 0
        for cell in layout.each_cell():
            shape_count += cell.shapes(layer_index).size()

        summaries.append(
            LayerSummary(
                layer=info.layer,
                datatype=info.datatype,
                name=info.name or None,
                visible=True,
                shape_count=shape_count,
            )
        )

    return sorted(summaries, key=lambda item: (item.layer, item.datatype))


def _micron_box(box: kdb.DBox) -> dict[str, float]:
    """Convert a KLayout `DBox` into rounded micron coordinates."""
    return {
        "left": round(box.left, 6),
        "bottom": round(box.bottom, 6),
        "right": round(box.right, 6),
        "top": round(box.top, 6),
    }


def _dbu_box(box: kdb.Box) -> dict[str, int]:
    """Convert a KLayout `Box` into integer database-unit coordinates."""
    return {
        "left": int(box.left),
        "bottom": int(box.bottom),
        "right": int(box.right),
        "top": int(box.top),
    }
