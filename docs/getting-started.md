# Getting Started

`klayout-mcp` runs as a stdio MCP server. The default launch shape is:

```text
command: uvx
args:    klayout-mcp@latest
```

If your client cannot use `uvx`, install the tool once and launch `klayout-mcp` directly.

## Required Environment

For batch DRC, the `klayout` executable must be on `PATH` or exposed through `KLAYOUT_BIN`.

```bash
export KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout
```

## Quick Smoke Test

After your MCP host starts the server, run this order:

1. `open_layout`
2. `list_layers`
3. `query_region`
4. `render_view`
5. `close_session`

That is enough to validate session handling, geometry inspection, and artifact generation.

## Runtime Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `KLAYOUT_MCP_ARTIFACT_ROOT` | Root directory for runtime artifacts | `<repo>/.artifacts` |
| `KLAYOUT_MCP_SESSION_TTL_SECONDS` | Session inactivity timeout | `3600` |
| `KLAYOUT_BIN` | KLayout batch executable for DRC | `klayout` |

Behavior:

- any absolute local path can be used for layouts and DRC scripts
- artifact paths returned by tools are absolute
- sessions expire lazily after inactivity
- `close_session` removes the session artifact directory
