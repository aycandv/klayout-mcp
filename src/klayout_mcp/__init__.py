"""Top-level package for the KLayout MCP server."""

from typing import Any


def build_server(*args: Any, **kwargs: Any):
    from .server import build_server as _build_server

    return _build_server(*args, **kwargs)


__all__ = ["build_server"]
