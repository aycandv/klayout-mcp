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
from tests.fixtures.layout_factory import build_waveguide_fixture


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
