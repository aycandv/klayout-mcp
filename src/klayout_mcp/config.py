"""Runtime configuration parsing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ARTIFACT_ROOT_ENV = "KLAYOUT_MCP_ARTIFACT_ROOT"
ALLOWED_LAYOUT_ROOTS_ENV = "KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS"
ALLOWED_DRC_ROOTS_ENV = "KLAYOUT_MCP_ALLOWED_DRC_ROOTS"
SESSION_TTL_SECONDS_ENV = "KLAYOUT_MCP_SESSION_TTL_SECONDS"
KLAYOUT_BIN_ENV = "KLAYOUT_BIN"


def _resolve_path(value: str, repo_root: Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def _parse_roots(raw_value: str | None, repo_root: Path) -> tuple[Path, ...]:
    if not raw_value:
        # Defaulting to the repo root keeps local fixtures usable while remaining bounded.
        return (repo_root,)

    roots = []
    for raw_item in raw_value.split(":"):
        item = raw_item.strip()
        if not item:
            continue
        roots.append(_resolve_path(item, repo_root))
    return tuple(roots)


@dataclass(slots=True, frozen=True)
class Settings:
    repo_root: Path
    artifact_root: Path
    allowed_layout_roots: tuple[Path, ...]
    allowed_drc_roots: tuple[Path, ...]
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
            allowed_layout_roots=_parse_roots(os.getenv(ALLOWED_LAYOUT_ROOTS_ENV), repo_root),
            allowed_drc_roots=_parse_roots(os.getenv(ALLOWED_DRC_ROOTS_ENV), repo_root),
            session_ttl_seconds=int(os.getenv(SESSION_TTL_SECONDS_ENV, "3600")),
            klayout_bin=os.getenv(KLAYOUT_BIN_ENV, "klayout"),
        )

    def is_path_allowed(self, path: Path, *, drc: bool = False) -> bool:
        candidate = path.expanduser().resolve()
        roots = self.allowed_drc_roots if drc else self.allowed_layout_roots
        return any(candidate == root or root in candidate.parents for root in roots)
