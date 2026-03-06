# klayout-mcp

MCP server for read-only KLayout inspection: open layouts, inspect hierarchy and geometry, render deterministic views, and run batch DRC decks with structured JSON results.

## Features

- Open `gds`, `gdsii`, `oas`, and `oasis` layout files
- List layers and cell hierarchy
- Query shapes and instances inside a bounding box
- Measure widths, gaps, lengths, overlap, and related geometry
- Render deterministic PNG views
- Run KLayout batch DRC scripts
- Extract DRC markers and optional crop images
- Return structured errors with stable error codes
- Enforce allowlisted roots for layout and DRC inputs

## Status

The server is functional over MCP `stdio`.

Current verification:

- automated suite: `23 passed`
- live MCP stdio smoke test completed successfully
- exercised against generated fixtures and a real GDS layout

Tested end-to-end flow:

1. `open_layout`
2. `list_layers`
3. `query_region`
4. `measure_geometry`
5. `render_view`
6. `run_drc_script`
7. `extract_markers`
8. `close_session`

## Requirements

- Python 3.11+
- `uv` recommended for environment management
- KLayout installed locally

The server uses KLayout's Python bindings for layout inspection and the `klayout` executable for batch DRC. If the executable is not on `PATH`, set `KLAYOUT_BIN`.

On macOS app installs, this is commonly:

```bash
export KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout
```

## Install

### Published Package

After `klayout-mcp` is published to PyPI, the simplest ways to run it will be:

```bash
uvx klayout-mcp
```

Or install it once and run the command directly:

```bash
uv tool install klayout-mcp
klayout-mcp
```

For MCP client configuration, this README uses `uvx` because that is the most common Python MCP pattern.

### Source Checkout

For unreleased builds or local development:

```bash
uv sync --extra dev
```

## Quick Start

Choose narrow allowlists for the layouts and DRC decks you want the server to access:

```bash
export KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS=/abs/path/to/layouts
export KLAYOUT_MCP_ALLOWED_DRC_ROOTS=/abs/path/to/drc-decks
export KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout
```

Start the server locally from a source checkout:

```bash
uv run klayout-mcp
```

The server speaks MCP over `stdio`.

## Using uv

For Python MCP servers, the common `uv` patterns are:

- `uvx <tool>` for published servers without a permanent install
- `uv tool install <tool>` when you want the command on your machine
- `uv --directory /path/to/repo run <tool>` for source checkouts

The recommended client configuration after PyPI release is:

```text
command: uvx
args:    klayout-mcp
```

That matches how many published Python MCP servers are configured in practice.

If your MCP host launches tools with a minimal `PATH`, replace `uvx` with its absolute path.

For a local source checkout, use:

```text
command: uv
args:    --directory /abs/path/to/klayout-mcp run klayout-mcp
```

## Commit Conventions

This repo uses Conventional Commits and checks them in two places:

- locally with `pre-commit` on the `commit-msg` hook
- in GitHub Actions on every push and pull request

Install the local hook once in a source checkout:

```bash
uv sync --extra dev
uv run pre-commit install --hook-type commit-msg --install-hooks
```

Allowed commit types:

- `build`
- `chore`
- `ci`
- `docs`
- `feat`
- `fix`
- `perf`
- `refactor`
- `revert`
- `style`
- `test`

## Client Setup

All clients below assume the package is published and launched with `uvx`:

```text
command: uvx
args:    klayout-mcp
```

Recommended environment variables:

- `KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS=/abs/path/to/layouts`
- `KLAYOUT_MCP_ALLOWED_DRC_ROOTS=/abs/path/to/drc-decks`
- `KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout`

If `klayout` is already on `PATH`, `KLAYOUT_BIN` is optional.

Ready-to-copy templates are in:

- `examples/mcp/codex.config.toml`
- `examples/mcp/claude-code.mcp.json`
- `examples/mcp/cursor.mcp.json`
- `examples/mcp/opencode.json`
- `examples/mcp/README.md`

For a source checkout before the first PyPI release, replace the launcher with:

```text
command: uv
args:    --directory /abs/path/to/klayout-mcp run klayout-mcp
```

### Codex

Codex reads MCP servers from `~/.codex/config.toml` or project-scoped `.codex/config.toml`.

```toml
[mcp_servers.klayout]
command = "uvx"
args = ["klayout-mcp"]

[mcp_servers.klayout.env]
KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS = "/abs/path/to/layouts"
KLAYOUT_MCP_ALLOWED_DRC_ROOTS = "/abs/path/to/drc-decks"
KLAYOUT_BIN = "/Applications/klayout.app/Contents/MacOS/klayout"
```

If you prefer the CLI, Codex also supports `codex mcp add`.

### Claude Code

Claude Code supports project-scoped `.mcp.json` files and user-scoped MCP configuration. For team use, project scope is the clearest option.

Create `.mcp.json` at the repo root:

```json
{
  "mcpServers": {
    "klayout": {
      "command": "uvx",
      "args": ["klayout-mcp"],
      "env": {
        "KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS": "/abs/path/to/layouts",
        "KLAYOUT_MCP_ALLOWED_DRC_ROOTS": "/abs/path/to/drc-decks",
        "KLAYOUT_BIN": "/Applications/klayout.app/Contents/MacOS/klayout"
      }
    }
  }
}
```

You can also add it from the CLI:

```bash
claude mcp add klayout --scope project \
  --env KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS=/abs/path/to/layouts \
  --env KLAYOUT_MCP_ALLOWED_DRC_ROOTS=/abs/path/to/drc-decks \
  --env KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout \
  -- uvx klayout-mcp
```

### Cursor

Cursor reads MCP servers from `.cursor/mcp.json` for a project or `~/.cursor/mcp.json` globally.

Create `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "klayout": {
      "command": "uvx",
      "args": ["klayout-mcp"],
      "env": {
        "KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS": "/abs/path/to/layouts",
        "KLAYOUT_MCP_ALLOWED_DRC_ROOTS": "/abs/path/to/drc-decks",
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
      "command": [
        "uvx",
        "klayout-mcp"
      ],
      "enabled": true,
      "environment": {
        "KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS": "/abs/path/to/layouts",
        "KLAYOUT_MCP_ALLOWED_DRC_ROOTS": "/abs/path/to/drc-decks",
        "KLAYOUT_BIN": "/Applications/klayout.app/Contents/MacOS/klayout"
      }
    }
  }
}
```

### Other MCP Clients And Agents

If your host asks for a local stdio server, use:

- command: `uvx`
- args: `["klayout-mcp"]`
- env: the three `KLAYOUT_*` variables above

For an unreleased source checkout, use:

- command: `uv`
- args: `["--directory", "/abs/path/to/klayout-mcp", "run", "klayout-mcp"]`
- env: the same `KLAYOUT_*` variables

This server is a good fit for agentic hosts because it is deterministic and read-only with respect to layout content, but it still writes render and DRC artifacts under the artifact root.

## Using With Agents

This server works with agentic clients, but you should keep the tool surface narrow.

- Point `KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS` at a small layout directory.
- Point `KLAYOUT_MCP_ALLOWED_DRC_ROOTS` at a small deck directory.
- Give write access to the artifact root because renders, reports, and marker crops are written there.
- Prefer project-scoped MCP config when you want team members or project-specific agents to share the same server setup.

Client-specific notes:

- Codex: if you use Codex multi-agent workflows, enable `features.multi_agent` in the same `config.toml` layer that declares the MCP server.
- Cursor: Cursor's Composer Agent can use enabled MCP tools directly from `Available Tools`.
- OpenCode: enabled MCP tools are available to the LLM and can be restricted per agent with `agent.<name>.tools`.

## Available Tools

### Session

- `open_layout`: open a layout and create a session
- `close_session`: close a session and delete its artifacts

### Structure

- `list_layers`: list layout layers in deterministic order
- `list_cells`: list cell hierarchy
- `describe_cell`: summarize one cell and its immediate structure

### Geometry

- `query_region`: return shapes, texts, and instances overlapping a box
- `measure_geometry`: measure geometry from shape ids returned by `query_region`

### View

- `set_view`: set the session view state
- `render_view`: render the current or requested view to PNG

### DRC

- `run_drc_script`: run a KLayout batch DRC script against the session layout
- `extract_markers`: return marker summaries and optional crop images

## Typical Workflow

For most users, the normal sequence is:

1. Open a layout with `open_layout`
2. Inspect its structure with `list_layers`, `list_cells`, or `describe_cell`
3. Focus on a region with `query_region`
4. Measure geometry from returned shape ids with `measure_geometry`
5. Render a view with `render_view`
6. Run a deck with `run_drc_script`
7. Inspect markers with `extract_markers`
8. Clean up with `close_session`

## Configuration

Supported environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `KLAYOUT_MCP_ARTIFACT_ROOT` | Root directory for runtime artifacts | `<repo>/.artifacts` |
| `KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS` | Colon-separated list of allowed layout roots | repo root |
| `KLAYOUT_MCP_ALLOWED_DRC_ROOTS` | Colon-separated list of allowed DRC script roots | repo root |
| `KLAYOUT_MCP_SESSION_TTL_SECONDS` | Session inactivity timeout | `3600` |
| `KLAYOUT_BIN` | KLayout batch executable for DRC | `klayout` |

Important behavior:

- layout and DRC paths outside the allowlists are rejected
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

Tool failures return structured JSON objects instead of free-form text:

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
- `PATH_NOT_ALLOWED`
- `SESSION_NOT_FOUND`
- `INVALID_BOX`
- `INVALID_LAYER`
- `INVALID_TARGET`
- `DRC_SCRIPT_NOT_ALLOWED`
- `DRC_RUN_FAILED`

## Security Notes

- This server is read-only with respect to layout content
- Input paths are restricted to configured allowlists
- DRC execution is limited to scripts under `KLAYOUT_MCP_ALLOWED_DRC_ROOTS`
- Tool parameters are treated as data, not shell fragments

Recommended practice:

- point `KLAYOUT_MCP_ALLOWED_LAYOUT_ROOTS` to a small layout directory
- point `KLAYOUT_MCP_ALLOWED_DRC_ROOTS` to a small deck directory
- avoid using broad roots like your home directory

## Current Limits

- tested transport is `stdio`
- no GUI attach mode
- no geometry editing
- no PCell authoring
- DRC usefulness depends on the deck matching the layout technology

## Development

Run tests:

```bash
./.venv/bin/python -m pytest -q
```

Run lint:

```bash
./.venv/bin/python -m ruff check .
```

## CI And Releases

Baseline GitHub Actions workflows are included:

- `.github/workflows/ci.yml`: runs `ruff`, `pytest`, `uv build`, and `twine check` on pushes to `main` and on pull requests
- `.github/workflows/release.yml`: manual publish workflow for `testpypi` or `pypi`

The release workflow follows the recommended Trusted Publishing shape:

- build distributions in one job
- upload them as artifacts
- publish from a separate job with `id-token: write`

Before the first release, configure GitHub and PyPI/TestPyPI:

1. Create GitHub environments named `testpypi` and `pypi`.
2. In TestPyPI and PyPI, add a Trusted Publisher for this repository.
3. Use workflow filename `.github/workflows/release.yml`.
4. Set the environment name to match the target index, `testpypi` or `pypi`.

Suggested release flow:

1. Update `version` in `pyproject.toml`.
2. Merge to `main`.
3. Run the `Release` workflow against `testpypi`.
4. Verify the published package.
5. Run the `Release` workflow against `pypi`.

This baseline does not automate changelogs, tags, or semantic version bumps yet.

## Reference Docs

- [docs/specs/2026-03-05-klayout-observer-mcp-contract.md](docs/specs/2026-03-05-klayout-observer-mcp-contract.md)
- [docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md](docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md)
- [docs/plans/2026-03-05-klayout-observer-mcp-design.md](docs/plans/2026-03-05-klayout-observer-mcp-design.md)

If those documents disagree, follow the contract.
