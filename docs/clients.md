# MCP Clients

More copy-paste examples live in the
[examples directory](https://github.com/aycandv/klayout-mcp/blob/main/examples/mcp/README.md).

## Codex

```toml
[mcp_servers.klayout]
command = "uvx"
args = ["klayout-mcp@latest"]

[mcp_servers.klayout.env]
KLAYOUT_BIN = "/Applications/klayout.app/Contents/MacOS/klayout"
```

CLI setup:

```bash
codex mcp add klayout \
  --env KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout \
  -- uvx klayout-mcp@latest
```

## Claude Code

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

CLI setup:

```bash
claude mcp add --transport stdio klayout \
  --scope project \
  --env KLAYOUT_BIN=/Applications/klayout.app/Contents/MacOS/klayout \
  -- uvx klayout-mcp@latest
```

## Cursor

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

## OpenCode

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

## Other MCP Hosts

Use:

- `command`: `uvx`
- `args`: `["klayout-mcp@latest"]`
- `env`: `KLAYOUT_BIN` when needed
