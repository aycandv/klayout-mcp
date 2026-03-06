"""Shared error types and codes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ERROR_CODES = frozenset(
    {
        "FILE_NOT_FOUND",
        "UNSUPPORTED_FORMAT",
        "TOP_CELL_NOT_FOUND",
        "SESSION_NOT_FOUND",
        "SESSION_EXPIRED",
        "INVALID_BOX",
        "INVALID_LAYER",
        "INVALID_TARGET",
        "QUERY_TOO_LARGE",
        "TOOL_LIMIT_EXCEEDED",
        "RENDER_FAILED",
        "DRC_RUN_FAILED",
        "INTERNAL_ERROR",
    }
)


@dataclass(slots=True, frozen=True)
class ErrorObject:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class KLayoutMCPError(Exception):
    """Structured application error with a contract-defined code."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"Unsupported error code: {code}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_error_object(self) -> ErrorObject:
        return ErrorObject(code=self.code, message=self.message, details=self.details)
