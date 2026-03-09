# ruff: noqa: E402

"""Shared pytest configuration."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
KLAYOUT_BIN = Path("/Applications/klayout.app/Contents/MacOS/klayout")

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from klayout_mcp.server import build_server
from tests.fixtures.layout_factory import (
    build_bend_fixture,
    build_curve_inspection_fixture,
    build_dense_fixture,
    build_directional_coupler_fixture,
    build_hierarchical_fixture,
    build_label_fixture,
    build_polygon_profile_fixture,
    build_violation_fixture,
    build_waveguide_fixture,
)


class MCPClient:
    def __init__(self) -> None:
        self._server = build_server()

    async def list_tool_names(self) -> set[str]:
        return {tool.name for tool in await self._server.list_tools()}

    async def call(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        _, structured = await self._server.call_tool(name, arguments)
        return structured

    async def call_expect_error(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        try:
            result = await self.call(name, arguments)
        except ToolError as exc:
            return {"code": None, "message": str(exc), "details": {}}

        if not isinstance(result, dict) or "code" not in result or "message" not in result:
            pytest.fail(f"Expected structured error result from {name}, got {result!r}")
        return result


@pytest.fixture
def mcp_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MCPClient:
    monkeypatch.setenv("KLAYOUT_MCP_ARTIFACT_ROOT", str(tmp_path / ".artifacts"))
    if KLAYOUT_BIN.exists():
        monkeypatch.setenv("KLAYOUT_BIN", str(KLAYOUT_BIN))
    return MCPClient()


@pytest.fixture
def generated_layout(tmp_path: Path):
    return build_waveguide_fixture(tmp_path)


@pytest.fixture
def generated_dense_layout(tmp_path: Path):
    return build_dense_fixture(tmp_path)


@pytest.fixture
def generated_curve_inspection_layout(tmp_path: Path):
    return build_curve_inspection_fixture(tmp_path)


@pytest.fixture
def generated_polygon_profile_layout(tmp_path: Path):
    return build_polygon_profile_fixture(tmp_path)


@pytest.fixture
def generated_bend_layout(tmp_path: Path):
    return build_bend_fixture(tmp_path)


@pytest.fixture
def generated_coupler_layout(tmp_path: Path):
    return build_directional_coupler_fixture(tmp_path)


@pytest.fixture
def generated_hierarchical_layout(tmp_path: Path):
    return build_hierarchical_fixture(tmp_path)


@pytest.fixture
def generated_label_layout(tmp_path: Path):
    return build_label_fixture(tmp_path)


@pytest.fixture
def generated_violation_layout(tmp_path: Path):
    return build_violation_fixture(tmp_path)


@pytest.fixture
async def opened_hierarchical_session(mcp_client: MCPClient, generated_hierarchical_layout) -> str:
    result = await mcp_client.call("open_layout", {"path": str(generated_hierarchical_layout.path)})
    return result["session_id"]


@pytest.fixture
async def opened_session(mcp_client: MCPClient, generated_layout) -> str:
    result = await mcp_client.call("open_layout", {"path": str(generated_layout.path)})
    return result["session_id"]


@pytest.fixture
async def opened_dense_session(mcp_client: MCPClient, generated_dense_layout) -> str:
    result = await mcp_client.call("open_layout", {"path": str(generated_dense_layout.path)})
    return result["session_id"]


@pytest.fixture
async def opened_curve_inspection_session(
    mcp_client: MCPClient,
    generated_curve_inspection_layout,
) -> str:
    result = await mcp_client.call(
        "open_layout",
        {"path": str(generated_curve_inspection_layout.path)},
    )
    return result["session_id"]


@pytest.fixture
async def opened_polygon_profile_session(
    mcp_client: MCPClient,
    generated_polygon_profile_layout,
) -> str:
    result = await mcp_client.call(
        "open_layout",
        {"path": str(generated_polygon_profile_layout.path)},
    )
    return result["session_id"]


@pytest.fixture
async def opened_bend_session(mcp_client: MCPClient, generated_bend_layout) -> str:
    result = await mcp_client.call("open_layout", {"path": str(generated_bend_layout.path)})
    return result["session_id"]


@pytest.fixture
async def opened_coupler_session(mcp_client: MCPClient, generated_coupler_layout) -> str:
    result = await mcp_client.call("open_layout", {"path": str(generated_coupler_layout.path)})
    return result["session_id"]


@pytest.fixture
async def opened_violation_session(mcp_client: MCPClient, generated_violation_layout) -> str:
    result = await mcp_client.call("open_layout", {"path": str(generated_violation_layout.path)})
    return result["session_id"]


@pytest.fixture
async def opened_label_session(mcp_client: MCPClient, generated_label_layout) -> str:
    result = await mcp_client.call("open_layout", {"path": str(generated_label_layout.path)})
    return result["session_id"]


@pytest.fixture
def drc_script(tmp_path: Path) -> Path:
    if not KLAYOUT_BIN.exists():
        pytest.skip("KLayout batch binary is not available")

    source = ROOT / "tests" / "fixtures" / "drc" / "min_space.drc"
    target = tmp_path / "min_space.drc"
    shutil.copyfile(source, target)
    return target


@pytest.fixture
async def completed_drc_run(
    mcp_client: MCPClient,
    opened_violation_session: str,
    drc_script: Path,
) -> dict[str, object]:
    return await mcp_client.call(
        "run_drc_script",
        {
            "session_id": opened_violation_session,
            "script_path": str(drc_script),
            "script_type": "ruby",
        },
    )


@pytest.fixture
async def queried_waveguide_region(mcp_client: MCPClient, opened_session) -> dict[str, object]:
    return await mcp_client.call(
        "query_region",
        {
            "session_id": opened_session,
            "box": {"left": 0.0, "bottom": -5.0, "right": 50.0, "top": 5.0},
            "hierarchy_mode": "recursive",
        },
    )


@pytest.fixture
async def queried_bend_region(mcp_client: MCPClient, opened_bend_session) -> dict[str, object]:
    return await mcp_client.call(
        "query_region",
        {
            "session_id": opened_bend_session,
            "box": {"left": 0.0, "bottom": -5.0, "right": 20.0, "top": 20.0},
            "hierarchy_mode": "recursive",
        },
    )


@pytest.fixture
async def queried_coupler_region(mcp_client: MCPClient, opened_coupler_session) -> dict[str, object]:
    return await mcp_client.call(
        "query_region",
        {
            "session_id": opened_coupler_session,
            "box": {"left": 0.0, "bottom": -5.0, "right": 40.0, "top": 10.0},
            "hierarchy_mode": "recursive",
        },
    )
