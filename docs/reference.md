# Reference

## Tools

- Session: `open_layout`, `close_session`
- Structure: `list_layers`, `list_cells`, `describe_cell`
- Geometry: `query_region`, `measure_geometry`, `analyze_waveguide`
- View: `set_view`, `render_view`
- DRC: `run_drc_script`, `extract_markers`

## Artifacts

Artifacts are stored under `.artifacts/sessions/<session_id>/` and include renders, DRC reports, marker crops, and logs.

`close_session` removes the session artifact directory.

## Errors

Tool failures return structured JSON such as:

```json
{
  "code": "FILE_NOT_FOUND",
  "message": "Layout file does not exist",
  "details": {
    "path": "/abs/path/to/missing.gds"
  }
}
```

Common codes:

- `FILE_NOT_FOUND`
- `SESSION_NOT_FOUND`
- `INVALID_BOX`
- `INVALID_LAYER`
- `INVALID_TARGET`
- `DRC_RUN_FAILED`

## Source Documents

- [Contract](specs/2026-03-05-klayout-observer-mcp-contract.md)
- [Design Plan](plans/2026-03-05-klayout-observer-mcp-design.md)
- [Implementation Plan](plans/2026-03-05-klayout-observer-mcp-implementation-plan.md)
- [PyPI Install Plan](plans/2026-03-06-pypi-install-plan.md)
