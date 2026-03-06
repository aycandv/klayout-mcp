"""Batch DRC execution and marker extraction helpers."""

from __future__ import annotations

import json
import re
import secrets
import subprocess
from pathlib import Path
from typing import Any

import klayout.db as kdb
import klayout.lay as klay
import klayout.rdb as rdb

from klayout_mcp.config import Settings
from klayout_mcp.errors import KLayoutMCPError

VALID_SCRIPT_TYPES = {"ruby"}
PARAM_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_CROP_SIZE_UM = {"x": 20.0, "y": 20.0}


def run_drc_script(
    *,
    session_id: str,
    settings: Settings,
    session: Any,
    runtime: dict[str, Any],
    script_path: str,
    script_type: str = "ruby",
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a batch KLayout DRC script and capture its artifacts.

    Args:
        session_id: Active session identifier.
        settings: Runtime process settings.
        session: Persisted session record.
        runtime: Session runtime state.
        script_path: Absolute path to the DRC deck.
        script_type: DRC script language.
        params: Optional runtime parameters passed through `-rd`.

    Returns:
        dict[str, Any]: DRC run summary and artifact metadata.

    Raises:
        KLayoutMCPError: If the script path, batch execution, or report is invalid.
    """
    resolved_script = _resolve_script_path(script_path, settings)
    normalized_type = _normalize_script_type(script_type)
    run_id = f"drc_{secrets.token_hex(4)}"
    run_dir = session.artifact_dir / "drc" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    layout_copy_path = run_dir / f"layout.{_layout_export_suffix(session.layout_format)}"
    report_path = run_dir / "report.lyrdb"
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    markers_path = run_dir / "markers.json"

    runtime["layout"].write(str(layout_copy_path))
    command = _batch_command(
        klayout_bin=settings.klayout_bin,
        script_path=resolved_script,
        layout_path=layout_copy_path,
        report_path=report_path,
        params=params or {},
    )

    completed = _run_batch(command=command, stdout_path=stdout_path, stderr_path=stderr_path)
    if completed.returncode != 0:
        raise KLayoutMCPError(
            "DRC_RUN_FAILED",
            "KLayout batch DRC run failed",
            {
                "session_id": session_id,
                "run_id": run_id,
                "script_path": str(resolved_script),
                "return_code": completed.returncode,
                "stdout_path": str(stdout_path.resolve()),
                "stderr_path": str(stderr_path.resolve()),
            },
        )
    if not report_path.exists():
        raise KLayoutMCPError(
            "DRC_RUN_FAILED",
            "DRC run did not produce a marker report",
            {
                "session_id": session_id,
                "run_id": run_id,
                "script_path": str(resolved_script),
                "report_path": str(report_path.resolve()),
            },
        )

    markers = _parse_report(report_path)
    markers_path.write_text(
        json.dumps({"markers": markers}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    rule_counts = _rule_counts(markers)
    runtime.setdefault("drc_runs", {})[run_id] = {
        "run_id": run_id,
        "script_path": str(resolved_script),
        "script_type": normalized_type,
        "layout_path": str(layout_copy_path.resolve()),
        "report_path": str(report_path.resolve()),
        "stdout_path": str(stdout_path.resolve()),
        "stderr_path": str(stderr_path.resolve()),
        "markers_path": str(markers_path.resolve()),
        "return_code": completed.returncode,
        "marker_count": len(markers),
        "rule_counts": dict(rule_counts),
    }

    return {
        "session_id": session_id,
        "run_id": run_id,
        "script_path": str(resolved_script),
        "script_type": normalized_type,
        "return_code": completed.returncode,
        "marker_count": len(markers),
        "rule_counts": dict(rule_counts),
        "artifacts": [
            _artifact("drc_report", report_path, "application/octet-stream"),
            _artifact("drc_markers", markers_path, "application/json"),
            _artifact("drc_stdout", stdout_path, "text/plain"),
            _artifact("drc_stderr", stderr_path, "text/plain"),
        ],
    }


def extract_markers(
    *,
    session_id: str,
    session: Any,
    runtime: dict[str, Any],
    run_id: str,
    include_crops: bool = False,
    crop_size_um: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return parsed DRC markers and optionally render per-marker crops.

    Args:
        session_id: Active session identifier.
        session: Persisted session record.
        runtime: Session runtime state.
        run_id: Prior DRC run identifier.
        include_crops: Whether to render marker crops.
        crop_size_um: Optional crop size override in microns.

    Returns:
        dict[str, Any]: Marker payload, optionally including crop artifacts.

    Raises:
        KLayoutMCPError: If the requested DRC run is not available.
    """
    drc_run = runtime.get("drc_runs", {}).get(run_id)
    if drc_run is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Requested DRC run was not found in the session",
            {"session_id": session_id, "run_id": run_id},
        )

    markers_path = Path(str(drc_run["markers_path"]))
    markers_payload = json.loads(markers_path.read_text(encoding="utf-8"))
    markers = list(markers_payload.get("markers", []))
    response_markers: list[dict[str, Any]] = []

    normalized_crop_size = _normalize_crop_size(crop_size_um) if include_crops else None
    run_dir = Path(str(drc_run["report_path"])).parent
    crops_dir = run_dir / "crops"
    layout_path = Path(str(drc_run["layout_path"]))

    for index, marker in enumerate(markers, start=1):
        marker_response = {
            "rule": marker["rule"],
            "box_um": dict(marker["box_um"]),
        }
        cell_name = str(marker.get("cell") or session.top_cell)
        if include_crops:
            crops_dir.mkdir(parents=True, exist_ok=True)
            crop_path = crops_dir / f"marker_{index:04d}.png"
            crop_box = _crop_box(marker["box_um"], normalized_crop_size)
            _render_crop(
                layout_path=layout_path,
                cell_name=cell_name,
                box_um=crop_box,
                output_path=crop_path,
            )
            marker_response["crop"] = _artifact("render", crop_path, "image/png")
        response_markers.append(marker_response)

    return {
        "session_id": session_id,
        "run_id": run_id,
        "markers": response_markers,
    }


def _resolve_script_path(script_path: str, settings: Settings) -> Path:
    """Validate and resolve the absolute DRC deck path."""
    candidate = Path(script_path).expanduser()
    if not candidate.is_absolute():
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "DRC script path must be absolute",
            {"script_path": script_path},
        )
    resolved = candidate.resolve()
    if not resolved.exists():
        raise KLayoutMCPError(
            "FILE_NOT_FOUND",
            "DRC script does not exist",
            {"script_path": str(resolved)},
        )
    return resolved


def _normalize_script_type(script_type: str) -> str:
    """Normalize the requested DRC script type."""
    normalized = script_type.strip().lower()
    if normalized not in VALID_SCRIPT_TYPES:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Unsupported DRC script type",
            {"script_type": script_type},
        )
    return normalized


def _layout_export_suffix(layout_format: str) -> str:
    """Return the file suffix used when exporting the session layout."""
    normalized = layout_format.lower()
    if normalized == "oasis":
        return "oas"
    return normalized


def _batch_command(
    *,
    klayout_bin: str,
    script_path: Path,
    layout_path: Path,
    report_path: Path,
    params: dict[str, str],
) -> list[str]:
    """Build the KLayout batch command line for one DRC run."""
    command = [
        klayout_bin,
        "-b",
        "-r",
        str(script_path),
        "-rd",
        f"input_path={layout_path.resolve()}",
        "-rd",
        f"report_path={report_path.resolve()}",
    ]
    for name in sorted(params):
        if PARAM_NAME_RE.fullmatch(name) is None:
            raise KLayoutMCPError(
                "INVALID_TARGET",
                "DRC parameter name is invalid",
                {"name": name},
            )
        command.extend(["-rd", f"{name}={params[name]}"])
    return command


def _run_batch(
    *,
    command: list[str],
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.CompletedProcess[str]:
    """Run the batch command and persist stdout and stderr artifacts."""
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as exc:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise KLayoutMCPError(
            "DRC_RUN_FAILED",
            "Failed to start KLayout batch process",
            {
                "command": command[0],
                "stderr_path": str(stderr_path.resolve()),
            },
        ) from exc

    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return completed


def _parse_report(report_path: Path) -> list[dict[str, Any]]:
    """Parse a `.lyrdb` report into deterministic marker dictionaries."""
    database = rdb.ReportDatabase()
    database.load(str(report_path))

    markers: list[dict[str, Any]] = []
    for item in database.each_item():
        box = _item_box(item)
        if box is None:
            continue

        category = database.category_by_id(item.category_id())
        cell = database.cell_by_id(item.cell_id())
        rule_name = category.path() or category.name()
        markers.append(
            {
                "rule": rule_name,
                "cell": cell.name() if cell is not None else None,
                "box_um": _box_to_dict(box),
            }
        )

    return sorted(
        markers,
        key=lambda marker: (
            marker["rule"],
            marker.get("cell") or "",
            marker["box_um"]["left"],
            marker["box_um"]["bottom"],
            marker["box_um"]["right"],
            marker["box_um"]["top"],
        ),
    )


def _item_box(item: Any) -> kdb.DBox | None:
    """Merge all item values into one bounding box when possible."""
    merged: kdb.DBox | None = None
    for value in item.each_value():
        current = _value_box(value)
        if current is None:
            continue
        if merged is None:
            merged = kdb.DBox(current.left, current.bottom, current.right, current.top)
            continue
        merged = kdb.DBox(
            min(merged.left, current.left),
            min(merged.bottom, current.bottom),
            max(merged.right, current.right),
            max(merged.top, current.top),
        )
    return merged


def _value_box(value: Any) -> kdb.DBox | None:
    """Return a bounding box for one report value variant."""
    if value.is_box():
        box = value.box()
        return kdb.DBox(box.left, box.bottom, box.right, box.top)
    if value.is_edge_pair():
        box = value.edge_pair().bbox()
        return kdb.DBox(box.left, box.bottom, box.right, box.top)
    if value.is_edge():
        box = value.edge().bbox()
        return kdb.DBox(box.left, box.bottom, box.right, box.top)
    if value.is_polygon():
        box = value.polygon().bbox()
        return kdb.DBox(box.left, box.bottom, box.right, box.top)
    if value.is_path():
        box = value.path().bbox()
        return kdb.DBox(box.left, box.bottom, box.right, box.top)
    return None


def _box_to_dict(box: kdb.DBox) -> dict[str, float]:
    """Convert a `DBox` into rounded micron coordinates."""
    return {
        "left": round(float(box.left), 6),
        "bottom": round(float(box.bottom), 6),
        "right": round(float(box.right), 6),
        "top": round(float(box.top), 6),
    }


def _rule_counts(markers: list[dict[str, Any]]) -> dict[str, int]:
    """Count markers by DRC rule name."""
    counts: dict[str, int] = {}
    for marker in markers:
        rule = str(marker["rule"])
        counts[rule] = counts.get(rule, 0) + 1
    return dict(sorted(counts.items()))


def _normalize_crop_size(crop_size_um: dict[str, float] | None) -> dict[str, float]:
    """Validate and normalize marker crop size in microns."""
    raw = crop_size_um or DEFAULT_CROP_SIZE_UM
    width = float(raw["x"])
    height = float(raw["y"])
    if width <= 0 or height <= 0:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Crop size must be positive",
            {"crop_size_um": raw},
        )
    return {"x": round(width, 6), "y": round(height, 6)}


def _crop_box(box_um: dict[str, float], crop_size_um: dict[str, float]) -> dict[str, float]:
    """Expand a marker box to the requested crop window."""
    left = float(box_um["left"])
    bottom = float(box_um["bottom"])
    right = float(box_um["right"])
    top = float(box_um["top"])
    center_x = (left + right) / 2.0
    center_y = (bottom + top) / 2.0
    half_width = max(crop_size_um["x"] / 2.0, (right - left) / 2.0)
    half_height = max(crop_size_um["y"] / 2.0, (top - bottom) / 2.0)
    return {
        "left": round(center_x - half_width, 6),
        "bottom": round(center_y - half_height, 6),
        "right": round(center_x + half_width, 6),
        "top": round(center_y + half_height, 6),
    }


def _render_crop(
    *,
    layout_path: Path,
    cell_name: str,
    box_um: dict[str, float],
    output_path: Path,
) -> None:
    """Render one marker crop from the exported layout copy."""
    view = klay.LayoutView()
    cellview_index = view.load_layout(str(layout_path))
    view.add_missing_layers()
    view.set_config("grid-visible", "false")
    view.set_config("background-color", "#ffffff")

    cellview = view.cellview(cellview_index)
    layout = cellview.layout()
    cell = layout.cell(cell_name)
    if cell is None:
        raise KLayoutMCPError(
            "INVALID_TARGET",
            "Requested marker cell was not found in the exported layout",
            {"cell": cell_name, "layout_path": str(layout_path.resolve())},
        )

    view.select_cell(cellview_index, cell.cell_index())
    view.zoom_box(kdb.DBox(box_um["left"], box_um["bottom"], box_um["right"], box_um["top"]))
    view.save_image(str(output_path), 512, 512)


def _artifact(kind: str, path: Path, media_type: str) -> dict[str, str]:
    """Return a standard artifact descriptor for a generated file."""
    return {
        "kind": kind,
        "path": str(path.resolve()),
        "media_type": media_type,
    }
