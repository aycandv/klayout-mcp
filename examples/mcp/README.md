# MCP Config Examples

These files are ready-to-copy templates for common MCP clients after `klayout-mcp` is published to PyPI:

- `codex.config.toml`
- `claude-code.mcp.json`
- `cursor.mcp.json`
- `opencode.json`

They use the published-package `uvx` pattern:

```text
uvx klayout-mcp
```

This is the recommended end-user setup because:

- it does not require a permanent install
- it matches common Python MCP server documentation
- it avoids hard-coding repo paths in client config

If your client does not inherit a reliable `PATH`, replace `uvx` with its absolute path.

Edit these placeholders before using the files:

- `KLAYOUT_BIN` if `klayout` is not already on `PATH`

For a source checkout before the first PyPI release, replace the launch command with:

```text
uv --directory /ABS/PATH/TO/klayout-mcp run klayout-mcp
```

If you prefer a permanently installed local command instead of `uvx`, install the package once:

```text
uv tool install klayout-mcp
```

Then set the client command to:

```text
klayout-mcp
```
