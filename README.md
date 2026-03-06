# klayout-mcp

Read-only MCP server for KLayout. It opens GDS/OAS layouts, inspects geometry and hierarchy, renders deterministic PNGs, and runs batch DRC with structured JSON output.

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

For batch DRC, the `klayout` executable must be on `PATH` or exposed through `KLAYOUT_BIN`.

```bash
export KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout
```

## Quick Start

`klayout-mcp` is a stdio MCP server. The default launch shape is:

```text
command: uvx
args:    klayout-mcp@latest
```

If your client cannot use `uvx`, install the tool once and launch `klayout-mcp` directly.

Typical workflow:

1. `open_layout`
2. `list_layers`
3. `list_cells` or `describe_cell`
4. `query_region`
5. `measure_geometry`
6. `render_view`
7. `run_drc_script`
8. `extract_markers`
9. `close_session`

## Client Setup

More copy-paste examples live in [examples/mcp/README.md](examples/mcp/README.md).

### Codex

```toml
[mcp_servers.klayout]
command = "uvx"
args = ["klayout-mcp@latest"]

[mcp_servers.klayout.env]
KLAYOUT_BIN = "/Applications/klayout.app/Contents/MacOS/klayout"
```

Or add it with the CLI:

```bash
codex mcp add klayout \
  --env KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout \
  -- uvx klayout-mcp@latest
```

### Claude Code

```json
{
  "mcpServers": {
    "klayout": {
      "command": "uvx",
      "args": ["klayout-mcp@latest"],
      "env": {
        "KLAYOUT_BIN": "/Applications/klayout.app/Contents/MacOS/klayout"
      }
    }
  }
}
```

Or add it with the CLI:

```bash
claude mcp add --transport stdio klayout \
  --scope project \
  --env KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout \
  -- uvx klayout-mcp@latest
```

### Cursor

Cursor is file-config based:

```json
{
  "mcpServers": {
    "klayout": {
      "command": "uvx",
      "args": ["klayout-mcp@latest"],
      "env": {
        "KLAYOUT_BIN": "/Applications/klayout.app/Contents/MacOS/klayout"
      }
    }
  }
}
```

### OpenCode

OpenCode is file-config based:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "klayout": {
      "type": "local",
      "command": ["uvx", "klayout-mcp@latest"],
      "enabled": true,
      "environment": {
        "KLAYOUT_BIN": "/Applications/klayout.app/Contents/MacOS/klayout"
      }
    }
  }
}
```

### Other MCP Hosts

Use:

- `command`: `uvx`
- `args`: `["klayout-mcp@latest"]`
- `env`: `KLAYOUT_BIN` when needed

## Tools

- Session: `open_layout`, `close_session`
- Structure: `list_layers`, `list_cells`, `describe_cell`
- Geometry: `query_region`, `measure_geometry`
- View: `set_view`, `render_view`
- DRC: `run_drc_script`, `extract_markers`

## Configuration

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

## Artifacts And Errors

Artifacts are stored under `.artifacts/sessions/<session_id>/` and include renders, DRC reports, marker crops, and logs.

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

Common codes: `FILE_NOT_FOUND`, `SESSION_NOT_FOUND`, `INVALID_BOX`, `INVALID_LAYER`, `INVALID_TARGET`, `DRC_RUN_FAILED`.

## Development

For a source checkout:

```bash
uv sync --extra dev
uv run klayout-mcp
```

If an MCP client needs to launch the checkout directly:

```text
command: uv
args:    --directory /abs/path/to/klayout-mcp run klayout-mcp
```

Contributor workflow is in [CONTRIBUTING.md](CONTRIBUTING.md). Release notes are in [CHANGELOG.md](CHANGELOG.md).

## Releases

Normal releases are automated with `release-please`.

- merge Conventional Commits to `main`
- `release-please` opens or updates a release PR
- merging that release PR updates `pyproject.toml`, `CHANGELOG.md`, creates the tag and GitHub release, and publishes to PyPI

To let the release PR run normal CI under branch protection, configure a repository secret named `RELEASE_PLEASE_TOKEN` with a GitHub token that can open pull requests. Without it, `release-please` falls back to `github.token`, which may not trigger PR workflows.

The manual [release.yml](/Users/avit/individual/klayout-mcp/.github/workflows/release.yml) workflow remains available for TestPyPI validation and recovery publishing.

## Reference

- [docs/specs/2026-03-05-klayout-observer-mcp-contract.md](docs/specs/2026-03-05-klayout-observer-mcp-contract.md)
- [docs/plans/2026-03-05-klayout-observer-mcp-design.md](docs/plans/2026-03-05-klayout-observer-mcp-design.md)
- [docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md](docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md)
