"""In-memory session tracking with artifact lifecycle management."""

from __future__ import annotations

import json
import secrets
import shutil
from datetime import timedelta
from pathlib import Path
from typing import Any

from .models import SessionRecord, utc_now


class SessionStore:
    def __init__(self, artifact_root: Path, ttl_seconds: int) -> None:
        self._artifact_root = artifact_root.expanduser().resolve()
        self._sessions_root = self._artifact_root / "sessions"
        self._sessions_root.mkdir(parents=True, exist_ok=True)
        self._ttl = timedelta(seconds=ttl_seconds)
        self._sessions: dict[str, SessionRecord] = {}
        self._runtime: dict[str, dict[str, Any]] = {}
        self._expired_session_ids: set[str] = set()

    @property
    def artifact_root(self) -> Path:
        return self._artifact_root

    def create_dummy_session(self) -> SessionRecord:
        return self.create_session(
            source_path=self._artifact_root / "dummy.gds",
            layout_format="gds",
            top_cell="TOP",
            dbu=0.001,
            metadata={"dummy": True},
        )

    def create_session(
        self,
        *,
        source_path: Path,
        layout_format: str,
        top_cell: str,
        dbu: float,
        metadata: dict[str, Any] | None = None,
        runtime: dict[str, Any] | None = None,
    ) -> SessionRecord:
        self._prune_expired()
        session_id = self._next_session_id()
        artifact_dir = self._session_dir(session_id)
        (artifact_dir / "renders").mkdir(parents=True, exist_ok=True)
        (artifact_dir / "drc").mkdir(parents=True, exist_ok=True)

        now = utc_now()
        session = SessionRecord(
            session_id=session_id,
            artifact_dir=artifact_dir,
            source_path=source_path.expanduser().resolve(),
            layout_format=layout_format,
            top_cell=top_cell,
            dbu=dbu,
            created_at=now,
            last_accessed_at=now,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        self._runtime[session_id] = runtime or {}
        self._write_session_file(session)
        return session

    def get(self, session_id: str) -> SessionRecord | None:
        self._prune_expired()
        session = self._sessions.get(session_id)
        if session is None:
            return None

        session.touch()
        self._write_session_file(session)
        return session

    def close(self, session_id: str) -> dict[str, bool | str]:
        self._prune_expired()
        session = self._sessions.pop(session_id, None)
        self._runtime.pop(session_id, None)
        self._expired_session_ids.discard(session_id)

        artifact_dir_deleted = False
        if session is not None and session.artifact_dir.exists():
            shutil.rmtree(session.artifact_dir)
            artifact_dir_deleted = True

        return {
            "session_id": session_id,
            "closed": session is not None,
            "artifact_dir_deleted": artifact_dir_deleted,
        }

    def was_expired(self, session_id: str) -> bool:
        self._prune_expired()
        return session_id in self._expired_session_ids

    def get_runtime(self, session_id: str) -> dict[str, Any] | None:
        return self._runtime.get(session_id)

    def _next_session_id(self) -> str:
        while True:
            session_id = f"ses_{secrets.token_hex(6)}"
            if session_id not in self._sessions:
                return session_id

    def _session_dir(self, session_id: str) -> Path:
        return self._sessions_root / session_id

    def _prune_expired(self) -> None:
        now = utc_now()
        for session_id, session in list(self._sessions.items()):
            if now - session.last_accessed_at <= self._ttl:
                continue

            self._expired_session_ids.add(session_id)
            self._sessions.pop(session_id, None)
            self._runtime.pop(session_id, None)
            if session.artifact_dir.exists():
                shutil.rmtree(session.artifact_dir)

    def _write_session_file(self, session: SessionRecord) -> None:
        session_file = session.artifact_dir / "session.json"
        session_file.write_text(
            json.dumps(session.to_json(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
