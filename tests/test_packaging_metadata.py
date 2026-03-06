import tomllib
from pathlib import Path


def test_project_declares_klayout_mcp_console_script():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    scripts = pyproject["project"]["scripts"]
    assert scripts["klayout-mcp"] == "klayout_mcp.server:main"
