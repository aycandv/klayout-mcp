# klayout-mcp

Observer-first MCP server for inspecting KLayout layouts, rendering deterministic views, and running existing DRC decks with structured outputs suitable for LLM workflows.

## Status

This repository has moved past handoff-only documentation. The current codebase includes:

- MCP server bootstrap with the fixed MVP tool names
- runtime settings parsing and allowlist handling
- in-memory session storage with artifact directories and TTL cleanup
- generated KLayout test fixtures for waveguide, bend, coupler, hierarchy, label, and DRC cases
- all 11 MVP tools implemented, including batch DRC execution and marker crop rendering
- structured contract errors returned as JSON objects with `code`, `message`, and `details`

The remaining planned work is Task 11 manual verification against a live MCP client.

## MVP Scope

The MVP is a Python-only server with a thin MCP layer over KLayout APIs:

- `klayout.db` for loading layouts and geometry inspection
- `klayout.lay` for deterministic rendering
- external `klayout -b -r` only for batch DRC execution

Out of scope for the MVP:

- geometry editing
- GUI attach mode
- PCell authoring
- arbitrary shell execution

## Implemented Tool Surface

The server exposes these contract-fixed tools:

- `open_layout`
- `close_session`
- `list_cells`
- `describe_cell`
- `list_layers`
- `query_region`
- `measure_geometry`
- `set_view`
- `render_view`
- `run_drc_script`
- `extract_markers`

## Repository Layout

```text
src/klayout_mcp/
  __init__.py
  bridge/
  config.py
  errors.py
  models.py
  server.py
  session_store.py
tests/
  fixtures/drc/min_space.drc
  fixtures/layout_factory.py
docs/
  specs/2026-03-05-klayout-observer-mcp-contract.md
  plans/2026-03-05-klayout-observer-mcp-design.md
  plans/2026-03-05-klayout-observer-mcp-implementation-plan.md
```

## Requirements

- Python 3.11+
- KLayout Python package available in the environment
- `uv` recommended for environment management

## Quick Start

Create a local environment and install dependencies:

```bash
uv venv --python python3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
```

Run the current test suite:

```bash
./.venv/bin/python -m pytest -q
```

Run the server over stdio:

```bash
./.venv/bin/python -m klayout_mcp.server
```

If KLayout is installed outside `PATH`, point `KLAYOUT_BIN` at the batch executable. On macOS app installs that is commonly:

```bash
export KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout
```

## Runtime Configuration

Supported environment variables:

- `KLAYOUT_MCP_ARTIFACT_ROOT`
  Default: `<repo>/.artifacts`
- `KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS`
  Colon-separated readable roots for layout inputs
- `KLAYOUT_MCP_ALLOWED_DRC_ROOTS`
  Colon-separated readable roots for DRC scripts
- `KLAYOUT_MCP_SESSION_TTL_SECONDS`
  Default: `3600`
- `KLAYOUT_BIN`
  Default: `klayout`

Paths outside the configured allowlists must be rejected. Session and render artifacts are stored under `.artifacts/sessions/<session_id>/...`.

Tool failures are returned as structured JSON objects:

```json
{
  "code": "FILE_NOT_FOUND",
  "message": "Layout file does not exist",
  "details": {
    "path": "/abs/path/to/missing.gds"
  }
}
```

## Source of Truth

Implementation should follow these documents in this order:

1. [docs/specs/2026-03-05-klayout-observer-mcp-contract.md](docs/specs/2026-03-05-klayout-observer-mcp-contract.md)
2. [docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md](docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md)
3. [docs/plans/2026-03-05-klayout-observer-mcp-design.md](docs/plans/2026-03-05-klayout-observer-mcp-design.md)

If the design brief and contract disagree, the contract wins.

## Development Notes

- Follow TDD strictly for behavior changes: write the failing test first, confirm the failure, then implement the minimum code to pass.
- Keep tool names, error codes, response field names, and artifact layout exactly aligned with the contract.
- Return absolute paths in tool responses.
- Preserve deterministic ordering and include both micron and dbu values where the contract requires them.
- Use `tests/fixtures/layout_factory.py` for synthetic layouts instead of checking binary fixtures into git.
