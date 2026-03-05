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
    layer: int
    datatype: int
    name: str | None
    visible: bool
    shape_count: int

    def to_response(self) -> dict[str, object]:
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
    requested_path = Path(path).expanduser()
    if not requested_path.is_absolute():
        raise KLayoutMCPError(
            "PATH_NOT_ALLOWED",
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
    if not settings.is_path_allowed(resolved_path):
        raise KLayoutMCPError(
            "PATH_NOT_ALLOWED",
            "Layout path is outside configured roots",
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
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_layers(layout: kdb.Layout) -> list[LayerSummary]:
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
    return {
        "left": round(box.left, 6),
        "bottom": round(box.bottom, 6),
        "right": round(box.right, 6),
        "top": round(box.top, 6),
    }


def _dbu_box(box: kdb.Box) -> dict[str, int]:
    return {
        "left": int(box.left),
        "bottom": int(box.bottom),
        "right": int(box.right),
        "top": int(box.top),
    }
