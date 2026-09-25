"""Runtime configuration parsing."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

ARTIFACT_ROOT_ENV = "KLAYOUT_MCP_ARTIFACT_ROOT"
SESSION_TTL_SECONDS_ENV = "KLAYOUT_MCP_SESSION_TTL_SECONDS"
KLAYOUT_BIN_ENV = "KLAYOUT_BIN"
APP_NAME = "klayout-mcp"


def _resolve_path(value: str, base_dir: Path) -> Path:
    """Resolve a user-provided path relative to a base directory."""
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def source_checkout_root() -> Path | None:
    """Return the repository root when running from a source checkout, else `None`.

    An installed package lives in `site-packages`, where the directory two levels above the
    package has no `pyproject.toml` or `src/klayout_mcp`.
    """
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "pyproject.toml").is_file() and (candidate / "src" / "klayout_mcp").is_dir():
        return candidate
    return None


def user_cache_dir() -> Path:
    """Return the per-user cache directory for this application on the current platform."""
    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME / "Cache"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / APP_NAME
    base = os.getenv("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / APP_NAME


@dataclass(slots=True, frozen=True)
class Settings:
    """Resolved runtime configuration for the MCP server process."""

    base_dir: Path
    artifact_root: Path
    session_ttl_seconds: int
    klayout_bin: str

    @classmethod
    def from_root(cls, root: Path) -> "Settings":
        """Build settings for a source checkout, keeping artifacts in `<root>/.artifacts`."""
        base_dir = root.expanduser().resolve()
        return cls._build(base_dir=base_dir, default_artifact_root=base_dir / ".artifacts")

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build settings for the running process.

        A source checkout keeps artifacts in `<repo>/.artifacts`. An installed package uses
        the per-user cache directory, and relative overrides resolve against the working
        directory.
        """
        checkout_root = source_checkout_root()
        if checkout_root is not None:
            return cls.from_root(checkout_root)
        return cls._build(base_dir=Path.cwd().resolve(), default_artifact_root=user_cache_dir())

    @classmethod
    def _build(cls, *, base_dir: Path, default_artifact_root: Path) -> "Settings":
        """Apply environment overrides and create the artifact root."""
        artifact_root_raw = os.getenv(ARTIFACT_ROOT_ENV)
        if artifact_root_raw:
            artifact_root = _resolve_path(artifact_root_raw, base_dir)
        else:
            artifact_root = default_artifact_root.expanduser().resolve()
        artifact_root.mkdir(parents=True, exist_ok=True)

        return cls(
            base_dir=base_dir,
            artifact_root=artifact_root,
            session_ttl_seconds=int(os.getenv(SESSION_TTL_SECONDS_ENV, "3600")),
            klayout_bin=os.getenv(KLAYOUT_BIN_ENV, "klayout"),
        )
