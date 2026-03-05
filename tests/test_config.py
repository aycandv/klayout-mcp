from pathlib import Path

from klayout_mcp.config import Settings


def test_default_artifact_root_is_repo_local(tmp_path: Path):
    settings = Settings.from_root(tmp_path)
    assert settings.artifact_root == tmp_path / ".artifacts"
