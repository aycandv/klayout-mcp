"""Runtime configuration parsing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ARTIFACT_ROOT_ENV = "KLAYOUT_MCP_ARTIFACT_ROOT"
SESSION_TTL_SECONDS_ENV = "KLAYOUT_MCP_SESSION_TTL_SECONDS"
KLAYOUT_BIN_ENV = "KLAYOUT_BIN"


def _resolve_path(value: str, repo_root: Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


@dataclass(slots=True, frozen=True)
class Settings:
    repo_root: Path
    artifact_root: Path
    session_ttl_seconds: int
    klayout_bin: str

    @classmethod
    def from_root(cls, root: Path) -> "Settings":
        repo_root = root.expanduser().resolve()

        artifact_root_raw = os.getenv(ARTIFACT_ROOT_ENV)
        if artifact_root_raw:
            artifact_root = _resolve_path(artifact_root_raw, repo_root)
        else:
            artifact_root = repo_root / ".artifacts"
        artifact_root.mkdir(parents=True, exist_ok=True)

        return cls(
            repo_root=repo_root,
            artifact_root=artifact_root,
            session_ttl_seconds=int(os.getenv(SESSION_TTL_SECONDS_ENV, "3600")),
            klayout_bin=os.getenv(KLAYOUT_BIN_ENV, "klayout"),
        )
