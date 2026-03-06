# Development

For a source checkout:

```bash
uv sync --extra dev --extra docs
uv run klayout-mcp
```

If an MCP client needs to launch the checkout directly:

```text
command: uv
args:    --directory /abs/path/to/klayout-mcp run klayout-mcp
```

## Documentation Site

Build the docs locally:

```bash
uv run --extra docs mkdocs build --strict
```

Serve the docs locally:

```bash
uv run --extra docs mkdocs serve
```

The repository is configured for Read the Docs with `.readthedocs.yaml` and `mkdocs.yml`. Import the GitHub repository into Read the Docs, and it can build directly from the default branch.

## Project Workflow

- Contributor workflow:
  [CONTRIBUTING.md](https://github.com/aycandv/klayout-mcp/blob/main/CONTRIBUTING.md)
- Release notes:
  [CHANGELOG.md](https://github.com/aycandv/klayout-mcp/blob/main/CHANGELOG.md)
- MCP config examples:
  [examples/mcp/README.md](https://github.com/aycandv/klayout-mcp/blob/main/examples/mcp/README.md)
