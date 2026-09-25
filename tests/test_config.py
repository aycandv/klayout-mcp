from pathlib import Path

from klayout_mcp import config
from klayout_mcp.config import Settings


def test_default_artifact_root_is_repo_local(tmp_path: Path):
    settings = Settings.from_root(tmp_path)
    assert settings.artifact_root == tmp_path / ".artifacts"


def test_source_checkout_keeps_repo_local_artifacts(monkeypatch):
    monkeypatch.delenv(config.ARTIFACT_ROOT_ENV, raising=False)
    checkout_root = config.source_checkout_root()

    assert checkout_root == Path(__file__).resolve().parents[1]
    assert Settings.from_environment().artifact_root == checkout_root / ".artifacts"


def test_installed_package_uses_user_cache_dir(tmp_path: Path, monkeypatch):
    monkeypatch.delenv(config.ARTIFACT_ROOT_ENV, raising=False)
    monkeypatch.setattr(config, "source_checkout_root", lambda: None)
    monkeypatch.setattr(config, "user_cache_dir", lambda: tmp_path / "cache" / "klayout-mcp")

    settings = Settings.from_environment()

    assert settings.artifact_root == (tmp_path / "cache" / "klayout-mcp").resolve()
    assert settings.artifact_root.is_dir()


def test_installed_package_resolves_relative_override_against_cwd(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "source_checkout_root", lambda: None)
    monkeypatch.setenv(config.ARTIFACT_ROOT_ENV, "artifacts")
    monkeypatch.chdir(tmp_path)

    assert Settings.from_environment().artifact_root == (tmp_path / "artifacts").resolve()


def test_user_cache_dir_follows_xdg_on_linux(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    assert config.user_cache_dir() == tmp_path / "klayout-mcp"
