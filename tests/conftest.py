# ruff: noqa: E402

"""Shared pytest configuration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from klayout_mcp.server import build_server
from tests.fixtures.layout_factory import (
    build_hierarchical_fixture,
    build_label_fixture,
    build_waveguide_fixture,
)


class MCPClient:
    def __init__(self) -> None:
        self._server = build_server()

    async def call(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        _, structured = await self._server.call_tool(name, arguments)
        return structured


@pytest.fixture
def mcp_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MCPClient:
    monkeypatch.setenv("KLAYOUT_MCP_ARTIFACT_ROOT", str(tmp_path / ".artifacts"))
    monkeypatch.setenv("KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS", str(tmp_path))
    monkeypatch.setenv("KLAYOUT_MCP_ALLOWED_DRC_ROOTS", str(tmp_path))
    return MCPClient()


@pytest.fixture
def generated_layout(tmp_path: Path):
    return build_waveguide_fixture(tmp_path)


@pytest.fixture
def generated_hierarchical_layout(tmp_path: Path):
    return build_hierarchical_fixture(tmp_path)


@pytest.fixture
def generated_label_layout(tmp_path: Path):
    return build_label_fixture(tmp_path)


@pytest.fixture
async def opened_hierarchical_session(mcp_client: MCPClient, generated_hierarchical_layout) -> str:
    result = await mcp_client.call("open_layout", {"path": str(generated_hierarchical_layout.path)})
    return result["session_id"]


@pytest.fixture
async def opened_label_session(mcp_client: MCPClient, generated_label_layout) -> str:
    result = await mcp_client.call("open_layout", {"path": str(generated_label_layout.path)})
    return result["session_id"]
