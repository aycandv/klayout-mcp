"""Programmatic KLayout fixtures used across the test suite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import klayout.db as kdb

from klayout_mcp.models import MicronBox

DBU = 0.001
WG_LAYER = (1, 0)
PIN_LAYER = (10, 0)
TEXT_LAYER = (100, 0)


@dataclass(slots=True, frozen=True)
class GeneratedLayoutFixture:
    name: str
    path: Path
    top_cell: str
    expected_layers: tuple[tuple[int, int], ...]
    expected_bbox_um: MicronBox


def build_waveguide_fixture(root: Path) -> GeneratedLayoutFixture:
    layout = _new_layout()
    top = layout.create_cell("TOP")
    wg = layout.layer(*WG_LAYER)
    top.shapes(wg).insert(kdb.DPath([kdb.DPoint(0, 0), kdb.DPoint(40, 0)], 0.5))
    return _write_fixture(root, "waveguide", layout, top, (WG_LAYER,))


def build_bend_fixture(root: Path) -> GeneratedLayoutFixture:
    layout = _new_layout()
    top = layout.create_cell("TOP")
    wg = layout.layer(*WG_LAYER)
    top.shapes(wg).insert(
        kdb.DPath(
            [kdb.DPoint(0, 0), kdb.DPoint(12, 0), kdb.DPoint(12, 12)],
            0.5,
        )
    )
    return _write_fixture(root, "bend", layout, top, (WG_LAYER,))


def build_directional_coupler_fixture(root: Path) -> GeneratedLayoutFixture:
    layout = _new_layout()
    top = layout.create_cell("TOP")
    wg = layout.layer(*WG_LAYER)
    top.shapes(wg).insert(kdb.DPath([kdb.DPoint(0, 0), kdb.DPoint(30, 0)], 0.5))
    top.shapes(wg).insert(kdb.DPath([kdb.DPoint(0, 1.2), kdb.DPoint(30, 1.2)], 0.5))
    return _write_fixture(root, "directional_coupler", layout, top, (WG_LAYER,))


def build_hierarchical_fixture(root: Path) -> GeneratedLayoutFixture:
    layout = _new_layout()
    child = layout.create_cell("CHILD")
    wg = layout.layer(*WG_LAYER)
    child.shapes(wg).insert(kdb.DBox(0, 0, 10, 2))

    top = layout.create_cell("TOP")
    top.insert(kdb.DCellInstArray(child.cell_index(), kdb.DCplxTrans(1.0, 0.0, False, 0.0, 0.0)))
    top.insert(kdb.DCellInstArray(child.cell_index(), kdb.DCplxTrans(1.0, 0.0, False, 15.0, 5.0)))
    return _write_fixture(root, "hierarchical", layout, top, (WG_LAYER,))


def build_label_fixture(root: Path) -> GeneratedLayoutFixture:
    layout = _new_layout()
    top = layout.create_cell("TOP")
    wg = layout.layer(*WG_LAYER)
    pins = layout.layer(*PIN_LAYER)
    text = layout.layer(*TEXT_LAYER)

    top.shapes(wg).insert(kdb.DPath([kdb.DPoint(0, 0), kdb.DPoint(25, 0)], 0.5))
    top.shapes(pins).insert(kdb.DBox(-0.5, -0.5, 0.5, 0.5))
    top.shapes(pins).insert(kdb.DBox(24.5, -0.5, 25.5, 0.5))
    top.shapes(text).insert(kdb.DText("PORT_IN", kdb.DTrans(0.0, 1.5)))
    top.shapes(text).insert(kdb.DText("PORT_OUT", kdb.DTrans(25.0, 1.5)))
    return _write_fixture(root, "labels", layout, top, (WG_LAYER, PIN_LAYER, TEXT_LAYER))


def build_all_fixtures(root: Path) -> dict[str, GeneratedLayoutFixture]:
    return {
        "waveguide": build_waveguide_fixture(root),
        "bend": build_bend_fixture(root),
        "directional_coupler": build_directional_coupler_fixture(root),
        "hierarchical": build_hierarchical_fixture(root),
        "labels": build_label_fixture(root),
    }


def _new_layout() -> kdb.Layout:
    layout = kdb.Layout()
    layout.dbu = DBU
    return layout


def _write_fixture(
    root: Path,
    name: str,
    layout: kdb.Layout,
    top_cell: kdb.Cell,
    expected_layers: tuple[tuple[int, int], ...],
) -> GeneratedLayoutFixture:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}.gds"
    layout.write(str(path))
    bbox = top_cell.dbbox()

    return GeneratedLayoutFixture(
        name=name,
        path=path,
        top_cell=top_cell.name,
        expected_layers=expected_layers,
        expected_bbox_um=MicronBox(
            left=bbox.left,
            bottom=bbox.bottom,
            right=bbox.right,
            top=bbox.top,
        ),
    )
