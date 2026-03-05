# KLayout Observer MCP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python-only, observer-first MCP server for KLayout that can open PIC layouts, inspect geometry, render deterministic images, and run existing DRC decks with machine-readable outputs.

**Architecture:** Implement one Python package with a thin MCP adapter over a KLayout bridge. The bridge owns session state, geometry queries, rendering, and DRC integration; the MCP layer owns input validation, tool registration, and error normalization. Headless deterministic mode is the only required runtime mode in MVP.

**Tech Stack:** Python 3.11+, official Python MCP SDK, `klayout.db`, `klayout.lay`, external `klayout` CLI for batch DRC, `pytest`, `pytest-cov`, `ruff`

---

**Repository precondition:** If this directory is not already a git repository, run `git init` before Task 1 so the commit checkpoints are valid.

### Task 1: Bootstrap the repository

**Files:**
- Create: `README.md`
- Create: `pyproject.toml`
- Create: `src/klayout_mcp/__init__.py`
- Create: `src/klayout_mcp/server.py`
- Create: `tests/conftest.py`
- Create: `tests/test_server_smoke.py`

**Step 1: Write the failing smoke test**

```python
from klayout_mcp.server import build_server


def test_build_server_exposes_expected_tool_names():
    server = build_server()
    tool_names = {tool.name for tool in server.list_tools()}
    assert "open_layout" in tool_names
    assert "render_view" in tool_names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_server_smoke.py -q`
Expected: FAIL with import or attribute errors because the package does not exist yet.

**Step 3: Write minimal implementation**

```python
EXPECTED_TOOLS = [
    "open_layout",
    "close_session",
    "list_cells",
    "describe_cell",
    "list_layers",
    "query_region",
    "measure_geometry",
    "set_view",
    "render_view",
    "run_drc_script",
    "extract_markers",
]
```

Expose `build_server()` from `src/klayout_mcp/server.py` and make the smoke test pass with placeholder tool registration.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_server_smoke.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md pyproject.toml src/klayout_mcp/__init__.py src/klayout_mcp/server.py tests/conftest.py tests/test_server_smoke.py
git commit -m "chore: bootstrap klayout mcp package"
```

### Task 2: Add configuration, errors, and session storage

**Files:**
- Create: `src/klayout_mcp/config.py`
- Create: `src/klayout_mcp/errors.py`
- Create: `src/klayout_mcp/models.py`
- Create: `src/klayout_mcp/session_store.py`
- Create: `tests/test_config.py`
- Create: `tests/test_session_store.py`

**Step 1: Write the failing tests**

```python
from pathlib import Path

from klayout_mcp.config import Settings
from klayout_mcp.session_store import SessionStore


def test_default_artifact_root_is_repo_local(tmp_path: Path):
    settings = Settings.from_root(tmp_path)
    assert settings.artifact_root == tmp_path / ".artifacts"


def test_session_store_closes_and_deletes_artifacts(tmp_path: Path):
    store = SessionStore(tmp_path, ttl_seconds=3600)
    session = store.create_dummy_session()
    assert store.close(session.session_id)["closed"] is True
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py tests/test_session_store.py -q`
Expected: FAIL because settings and session store are not implemented.

**Step 3: Implement minimal settings and store**

```python
@dataclass(slots=True)
class Settings:
    artifact_root: Path
    allowed_layout_roots: tuple[Path, ...]
    allowed_drc_roots: tuple[Path, ...]
    session_ttl_seconds: int
    klayout_bin: str
```

Implement:
- env parsing
- allowlist checks
- artifact directory creation
- lazy TTL cleanup
- explicit close semantics

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py tests/test_session_store.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/config.py src/klayout_mcp/errors.py src/klayout_mcp/models.py src/klayout_mcp/session_store.py tests/test_config.py tests/test_session_store.py
git commit -m "feat: add config and session storage"
```

### Task 3: Create programmatic layout fixtures

**Files:**
- Create: `tests/fixtures/layout_factory.py`
- Create: `tests/test_layout_factory.py`

**Step 1: Write the failing fixture test**

```python
from tests.fixtures.layout_factory import build_waveguide_fixture


def test_waveguide_fixture_has_expected_top_cell_and_layers(tmp_path):
    fixture = build_waveguide_fixture(tmp_path)
    assert fixture.top_cell == "TOP"
    assert fixture.path.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_layout_factory.py -q`
Expected: FAIL because the fixture factory does not exist.

**Step 3: Implement the minimal fixture factory**

Generate at least these synthetic layouts through KLayout APIs:
- straight waveguide
- simple bend
- directional coupler
- hierarchical two-cell layout
- text-label fixture for port spacing tests

Return a small metadata object with:
- `path`
- `top_cell`
- `expected_layers`
- `expected_bbox_um`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_layout_factory.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/fixtures/layout_factory.py tests/test_layout_factory.py
git commit -m "test: add generated klayout fixtures"
```

### Task 4: Implement `open_layout`, `close_session`, and `list_layers`

**Files:**
- Create: `src/klayout_mcp/bridge/layout_loader.py`
- Create: `src/klayout_mcp/tools/layout_tools.py`
- Modify: `src/klayout_mcp/server.py`
- Create: `tests/test_open_layout.py`
- Create: `tests/test_list_layers.py`

**Step 1: Write the failing tests**

```python
def test_open_layout_returns_session_and_bbox(mcp_client, generated_layout):
    result = mcp_client.call("open_layout", {"path": str(generated_layout.path)})
    assert result["session_id"].startswith("ses_")
    assert result["selected_top_cell"] == generated_layout.top_cell


def test_list_layers_reports_numeric_layers(mcp_client, opened_session):
    result = mcp_client.call("list_layers", {"session_id": opened_session})
    assert result["layers"][0]["layer"] >= 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_open_layout.py tests/test_list_layers.py -q`
Expected: FAIL because these tools do not exist yet.

**Step 3: Implement minimal tools**

`layout_loader.py` should:
- validate absolute path
- validate allowed roots
- infer format
- load layout through `klayout.db.Layout`
- compute top cells, dbu, bbox, and layer list

`layout_tools.py` should:
- open the session
- close the session
- list layers in deterministic order

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_open_layout.py tests/test_list_layers.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/layout_loader.py src/klayout_mcp/tools/layout_tools.py src/klayout_mcp/server.py tests/test_open_layout.py tests/test_list_layers.py
git commit -m "feat: add layout open and layer inspection tools"
```

### Task 5: Implement `list_cells` and `describe_cell`

**Files:**
- Create: `src/klayout_mcp/bridge/hierarchy.py`
- Create: `tests/test_list_cells.py`
- Create: `tests/test_describe_cell.py`
- Modify: `src/klayout_mcp/tools/layout_tools.py`
- Modify: `src/klayout_mcp/server.py`

**Step 1: Write the failing tests**

```python
def test_list_cells_returns_sorted_cell_names(mcp_client, opened_hierarchical_session):
    result = mcp_client.call("list_cells", {"session_id": opened_hierarchical_session, "max_depth": 2})
    names = [cell["name"] for cell in result["cells"]]
    assert names == sorted(names)


def test_describe_cell_returns_instance_and_label_data(mcp_client, opened_hierarchical_session):
    result = mcp_client.call("describe_cell", {"session_id": opened_hierarchical_session, "cell": "TOP", "depth": 1})
    assert "instances" in result
    assert "shape_counts_by_layer" in result
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_list_cells.py tests/test_describe_cell.py -q`
Expected: FAIL because hierarchy helpers are not implemented.

**Step 3: Implement minimal hierarchy support**

Support:
- sorted cell enumeration
- child instance counting
- bbox collection
- depth-limited description
- label extraction
- simple transform serialization

Use plain dictionaries or Pydantic models, but the serialized field names must match the contract.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_list_cells.py tests/test_describe_cell.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/hierarchy.py src/klayout_mcp/tools/layout_tools.py src/klayout_mcp/server.py tests/test_list_cells.py tests/test_describe_cell.py
git commit -m "feat: add cell hierarchy inspection tools"
```

### Task 6: Implement `query_region`

**Files:**
- Create: `src/klayout_mcp/bridge/query.py`
- Create: `tests/test_query_region.py`
- Modify: `src/klayout_mcp/tools/layout_tools.py`
- Modify: `src/klayout_mcp/models.py`
- Modify: `src/klayout_mcp/server.py`

**Step 1: Write the failing tests**

```python
def test_query_region_returns_shape_refs(mcp_client, opened_session):
    result = mcp_client.call(
        "query_region",
        {
            "session_id": opened_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 50.0, "top": 20.0},
            "hierarchy_mode": "recursive",
        },
    )
    assert result["shapes"]
    assert result["shapes"][0]["id"].startswith("shp_")


def test_query_region_reports_truncation(mcp_client, opened_dense_session):
    result = mcp_client.call(
        "query_region",
        {
            "session_id": opened_dense_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 500.0, "top": 500.0},
            "max_shapes": 1,
        },
    )
    assert result["truncation"]["shapes_dropped"] >= 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_query_region.py -q`
Expected: FAIL because region query and stable shape refs do not exist.

**Step 3: Implement region query logic**

Support:
- box validation
- layer filtering
- hierarchy modes: `top`, `recursive`, `flattened`
- deterministic shape ordering
- shape IDs stable within a session
- truncation metadata

Shape summaries should include:
- `id`
- `kind`
- `cell`
- `instance_path`
- `layer`
- `bbox_um`
- shape-specific lightweight stats such as `point_count` or `path_width_um`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_query_region.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/query.py src/klayout_mcp/tools/layout_tools.py src/klayout_mcp/models.py src/klayout_mcp/server.py tests/test_query_region.py
git commit -m "feat: add bounded region queries"
```

### Task 7: Implement `measure_geometry`

**Files:**
- Create: `src/klayout_mcp/bridge/measure.py`
- Create: `tests/test_measure_geometry.py`
- Modify: `src/klayout_mcp/tools/layout_tools.py`
- Modify: `src/klayout_mcp/server.py`

**Step 1: Write the failing tests**

```python
def test_measure_geometry_reports_path_width(mcp_client, queried_waveguide_region):
    target_id = queried_waveguide_region["shapes"][0]["id"]
    result = mcp_client.call("measure_geometry", {"session_id": queried_waveguide_region["session_id"], "mode": "path_width", "target_ids": [target_id]})
    assert result["value_um"] > 0


def test_measure_geometry_reports_edge_gap_for_coupler(mcp_client, queried_coupler_region):
    ids = [shape["id"] for shape in queried_coupler_region["shapes"][:2]]
    result = mcp_client.call("measure_geometry", {"session_id": queried_coupler_region["session_id"], "mode": "edge_gap", "target_ids": ids})
    assert result["value_um"] >= 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_measure_geometry.py -q`
Expected: FAIL because measurement logic does not exist.

**Step 3: Implement minimal measurement modes**

Implement:
- `path_width`
- `segment_length`
- `centerline_distance`
- `edge_gap`
- `bend_radius_estimate`
- `overlap`

Implement `label_distance` and `port_spacing` after shape-based modes are passing.

Use lightweight geometry methods first. Do not overfit to photonic semantics in MVP.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_measure_geometry.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/measure.py src/klayout_mcp/tools/layout_tools.py src/klayout_mcp/server.py tests/test_measure_geometry.py
git commit -m "feat: add geometry measurement tools"
```

### Task 8: Implement `set_view` and `render_view`

**Files:**
- Create: `src/klayout_mcp/bridge/render.py`
- Create: `tests/test_render_view.py`
- Modify: `src/klayout_mcp/tools/layout_tools.py`
- Modify: `src/klayout_mcp/session_store.py`
- Modify: `src/klayout_mcp/server.py`

**Step 1: Write the failing tests**

```python
from pathlib import Path


def test_render_view_writes_png(mcp_client, opened_session):
    result = mcp_client.call(
        "render_view",
        {
            "session_id": opened_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 50.0, "top": 20.0},
            "image_size": {"width": 800, "height": 600},
            "style": "light",
        },
    )
    assert Path(result["image"]["path"]).exists()


def test_set_view_updates_session_defaults(mcp_client, opened_session):
    result = mcp_client.call(
        "set_view",
        {
            "session_id": opened_session,
            "box": {"left": 0.0, "bottom": 0.0, "right": 25.0, "top": 10.0},
        },
    )
    assert result["view"]["box_um"]["right"] == 25.0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_view.py -q`
Expected: FAIL because rendering and persisted view state do not exist.

**Step 3: Implement rendering**

Use `klayout.lay.LayoutView` with deterministic inputs:
- explicit cell
- explicit layer visibility
- explicit image size
- explicit bbox

Implementation notes:
- keep rendering isolated in one module
- persist updated view defaults into the session store
- if standalone rendering produces blank images, add the required view refresh or timer call before `save_image_with_options`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render_view.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/render.py src/klayout_mcp/tools/layout_tools.py src/klayout_mcp/session_store.py src/klayout_mcp/server.py tests/test_render_view.py
git commit -m "feat: add deterministic rendering tools"
```

### Task 9: Implement `run_drc_script` and `extract_markers`

**Files:**
- Create: `src/klayout_mcp/bridge/drc.py`
- Create: `tests/test_run_drc_script.py`
- Create: `tests/test_extract_markers.py`
- Create: `tests/fixtures/drc/min_space.drc`
- Modify: `src/klayout_mcp/tools/layout_tools.py`
- Modify: `src/klayout_mcp/server.py`

**Step 1: Write the failing tests**

```python
def test_run_drc_script_returns_marker_summary(mcp_client, opened_violation_session, drc_script):
    result = mcp_client.call(
        "run_drc_script",
        {
            "session_id": opened_violation_session,
            "script_path": str(drc_script),
            "script_type": "ruby",
        },
    )
    assert result["marker_count"] >= 1


def test_extract_markers_can_render_crops(mcp_client, completed_drc_run):
    result = mcp_client.call(
        "extract_markers",
        {
            "session_id": completed_drc_run["session_id"],
            "run_id": completed_drc_run["run_id"],
            "include_crops": True,
            "crop_size_um": {"x": 20.0, "y": 20.0},
        },
    )
    assert result["markers"][0]["crop"]["path"].endswith(".png")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_run_drc_script.py tests/test_extract_markers.py -q`
Expected: FAIL because batch DRC integration and marker parsing do not exist.

**Step 3: Implement DRC integration**

Support:
- script allowlist validation
- temp export of session layout into run directory
- batch invocation through `klayout -b -r`
- marker artifact discovery
- rule aggregation
- optional crop rendering around marker boxes

Keep stdout and stderr artifacts for debugging even on success.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_run_drc_script.py tests/test_extract_markers.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/klayout_mcp/bridge/drc.py src/klayout_mcp/tools/layout_tools.py src/klayout_mcp/server.py tests/test_run_drc_script.py tests/test_extract_markers.py tests/fixtures/drc/min_space.drc
git commit -m "feat: add batch drc execution and marker extraction"
```

### Task 10: Add integration coverage and polish

**Files:**
- Create: `tests/test_contract_smoke.py`
- Create: `tests/test_error_paths.py`
- Modify: `README.md`
- Modify: `docs/specs/2026-03-05-klayout-observer-mcp-contract.md`

**Step 1: Write the failing contract tests**

```python
def test_all_contract_tool_names_exist(mcp_client):
    names = set(mcp_client.list_tool_names())
    assert names == {
        "open_layout",
        "close_session",
        "list_cells",
        "describe_cell",
        "list_layers",
        "query_region",
        "measure_geometry",
        "set_view",
        "render_view",
        "run_drc_script",
        "extract_markers",
    }


def test_invalid_path_returns_contract_error_code(mcp_client):
    result = mcp_client.call_expect_error("open_layout", {"path": "/tmp/missing.gds"})
    assert result["code"] in {"FILE_NOT_FOUND", "PATH_NOT_ALLOWED"}
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_contract_smoke.py tests/test_error_paths.py -q`
Expected: FAIL until error normalization and contract parity are complete.

**Step 3: Polish implementation and docs**

Ensure:
- all tool names match the contract
- errors use exact codes
- README explains local run flow
- contract doc matches actual behavior
- artifact paths are absolute

**Step 4: Run the full suite**

Run: `pytest -q`
Expected: PASS

Run: `ruff check .`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md docs/specs/2026-03-05-klayout-observer-mcp-contract.md tests/test_contract_smoke.py tests/test_error_paths.py
git commit -m "chore: finalize contract coverage and docs"
```

### Task 11: Manual verification

**Files:**
- No code changes expected

**Step 1: Open a generated or real GDS**

Run: `python -m klayout_mcp.server`
Expected: MCP server starts without crashing.

**Step 2: Exercise the core flow manually**

Call tools in this order:
- `open_layout`
- `list_layers`
- `query_region`
- `measure_geometry`
- `render_view`

Expected:
- all responses are structured JSON
- render PNG exists
- measurements report both microns and dbu values

**Step 3: Exercise one DRC run**

Call:
- `run_drc_script`
- `extract_markers`

Expected:
- `.lyrdb` or machine-readable marker artifact exists
- marker summaries are returned
- crop images exist when requested

**Step 4: Record any mismatches**

Update:
- `README.md`
- `docs/specs/2026-03-05-klayout-observer-mcp-contract.md`

Only if behavior differs for defensible reasons.

**Step 5: Final commit**

```bash
git add README.md docs/specs/2026-03-05-klayout-observer-mcp-contract.md
git commit -m "docs: reconcile manual verification notes"
```
