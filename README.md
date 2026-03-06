# klayout-mcp

Read-only MCP server for KLayout. It opens GDS/OAS layouts, inspects hierarchy and geometry, renders deterministic PNG views, and runs batch DRC with structured JSON results.

## Install In 60 Seconds

Fastest one-off run:

```bash
uvx klayout-mcp
```

Install once and keep the command on your machine:

```bash
uv tool install klayout-mcp
klayout-mcp
```

Traditional Python install:

```bash
python -m pip install klayout-mcp
```

`klayout-mcp` depends on the `klayout` Python package. For batch DRC, you also need the `klayout` executable on `PATH` or `KLAYOUT_BIN` set explicitly.

Common macOS app path:

```bash
export KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout
```

## Quick Start

Set `KLAYOUT_BIN` if the `klayout` executable is not already on `PATH`:

```bash
export KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout
```

The server speaks MCP over `stdio`. The most common launcher is:

```text
command: uvx
args:    klayout-mcp
```

If your host cannot use `uvx`, install once with `uv tool install klayout-mcp` and point the client at the installed `klayout-mcp` binary instead.

## Choose Your Client

Ready-to-copy config files live in [examples/mcp/README.md](examples/mcp/README.md).

### Codex

Codex supports user-scoped `~/.codex/config.toml` and project-scoped `.codex/config.toml`.

```toml
[mcp_servers.klayout]
command = "uvx"
args = ["klayout-mcp"]

[mcp_servers.klayout.env]
KLAYOUT_BIN = "/Applications/klayout.app/Contents/MacOS/klayout"
```

Codex CLI also supports adding stdio servers directly:

```bash
codex mcp add klayout \
  --env KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout \
  -- uvx klayout-mcp
```

### Claude Code

Claude Code supports project-scoped `.mcp.json` and user-scoped MCP configuration.

```json
{
  "mcpServers": {
    "klayout": {
      "command": "uvx",
      "args": ["klayout-mcp"],
      "env": {
        "KLAYOUT_BIN": "/Applications/klayout.app/Contents/MacOS/klayout"
      }
    }
  }
}
```

CLI form:

```bash
claude mcp add klayout --scope project \
  --env KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout \
  -- uvx klayout-mcp
```

### Cursor

Cursor reads MCP servers from `.cursor/mcp.json` for a project or `~/.cursor/mcp.json` globally.

```json
{
  "mcpServers": {
    "klayout": {
      "command": "uvx",
      "args": ["klayout-mcp"],
      "env": {
        "KLAYOUT_BIN": "/Applications/klayout.app/Contents/MacOS/klayout"
      }
    }
  }
}
```

### OpenCode

OpenCode reads MCP servers from `opencode.json` under the `mcp` key.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "klayout": {
      "type": "local",
      "command": ["uvx", "klayout-mcp"],
      "enabled": true,
      "environment": {
        "KLAYOUT_BIN": "/Applications/klayout.app/Contents/MacOS/klayout"
      }
    }
  }
}
```

### Other MCP Hosts And Agents

Use this stdio shape:

- `command`: `uvx`
- `args`: `["klayout-mcp"]`
- `env`: `KLAYOUT_BIN` when needed

This server works well with agents because it is read-only with respect to layout content, but it still writes artifacts for renders, reports, and marker crops.

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

## Available Tools

### Session

- `open_layout`
- `close_session`

### Structure

- `list_layers`
- `list_cells`
- `describe_cell`

### Geometry

- `query_region`
- `measure_geometry`

### View

- `set_view`
- `render_view`

### DRC

- `run_drc_script`
- `extract_markers`

## Configuration

Supported environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `KLAYOUT_MCP_ARTIFACT_ROOT` | Root directory for runtime artifacts | `<repo>/.artifacts` |
| `KLAYOUT_MCP_SESSION_TTL_SECONDS` | Session inactivity timeout | `3600` |
| `KLAYOUT_BIN` | KLayout batch executable for DRC | `klayout` |

Important behavior:

- any absolute local path can be used for layouts and DRC scripts
- artifact paths returned by tools are absolute
- sessions expire lazily after inactivity
- `close_session` removes the session artifact directory

## Artifacts

Runtime artifacts are stored under:

```text
.artifacts/
  sessions/
    <session_id>/
      session.json
      renders/
      drc/
```

Typical outputs include:

- rendered PNGs
- DRC reports (`.lyrdb`)
- `markers.json`
- `stdout.txt` and `stderr.txt`
- crop images for extracted markers

## Error Model

Tool failures return structured JSON objects:

```json
{
  "code": "FILE_NOT_FOUND",
  "message": "Layout file does not exist",
  "details": {
    "path": "/abs/path/to/missing.gds"
  }
}
```

Common codes include:

- `FILE_NOT_FOUND`
- `SESSION_NOT_FOUND`
- `INVALID_BOX`
- `INVALID_LAYER`
- `INVALID_TARGET`
- `DRC_RUN_FAILED`

## Security Notes

- This server is read-only with respect to layout content
- any absolute local layout path or DRC script path may be used
- tool parameters are treated as data, not shell fragments

## Source Checkout

For local development or unreleased builds:

```bash
uv sync --extra dev
uv run klayout-mcp
```

If an MCP client needs to launch a source checkout directly:

```text
command: uv
args:    --directory /abs/path/to/klayout-mcp run klayout-mcp
```

Contributor workflow, branch policy, and release expectations are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

## CI And Releases

GitHub Actions workflows included in this repo:

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `.github/workflows/github-release.yml`

Human-readable release notes live in [CHANGELOG.md](CHANGELOG.md).

Release flow:

1. Update `version` in `pyproject.toml`
2. Move `Unreleased` notes into a new version section in `CHANGELOG.md`
3. Merge to `main`
4. Run the `Release` workflow for `testpypi`
5. Verify the package from TestPyPI
6. Run the `Release` workflow for `pypi`
7. Push the matching tag, for example `v0.1.0`

## Reference Docs

- [docs/specs/2026-03-05-klayout-observer-mcp-contract.md](docs/specs/2026-03-05-klayout-observer-mcp-contract.md)
- [docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md](docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md)
- [docs/plans/2026-03-05-klayout-observer-mcp-design.md](docs/plans/2026-03-05-klayout-observer-mcp-design.md)

If those documents disagree, follow the contract.
