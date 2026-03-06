# klayout-mcp

`klayout-mcp` is a read-only MCP server for KLayout. It opens GDS/OAS layouts, inspects geometry and hierarchy, renders deterministic PNGs, and runs batch DRC with structured JSON output.

## What It Covers

- Open a layout and inspect layers, cells, and hierarchy
- Query geometry in bounded regions and measure shapes
- Render deterministic view images for layouts and markers
- Run batch DRC decks and extract marker crops

## Install

Fastest one-off run:

```bash
uvx klayout-mcp@latest
```

Install once:

```bash
uv tool install klayout-mcp
```

Traditional Python install:

```bash
python -m pip install klayout-mcp
```

If you use batch DRC, make sure the `klayout` executable is on `PATH` or exported through `KLAYOUT_BIN`.

## Typical Workflow

1. `open_layout`
2. `list_layers`
3. `list_cells` or `describe_cell`
4. `query_region`
5. `measure_geometry`
6. `render_view`
7. `run_drc_script`
8. `extract_markers`
9. `close_session`

Continue with [Getting Started](getting-started.md) for the shortest local setup path, or jump to [MCP Clients](clients.md) for Codex, Claude Code, Cursor, and OpenCode examples.
