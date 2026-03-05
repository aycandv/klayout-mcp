# klayout-mcp

Observer-first MCP server design and handoff package for KLayout-based photonic layout inspection.

## Status

This repository currently contains a handoff package only. Implementation has not started.

The directory is not initialized as a git repository yet, so the execution agent should run `git init` before following any commit checkpoints in the implementation plan.

## Start Here

- Design brief: [docs/plans/2026-03-05-klayout-observer-mcp-design.md](docs/plans/2026-03-05-klayout-observer-mcp-design.md)
- Exact MCP contract: [docs/specs/2026-03-05-klayout-observer-mcp-contract.md](docs/specs/2026-03-05-klayout-observer-mcp-contract.md)
- Execution plan: [docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md](docs/plans/2026-03-05-klayout-observer-mcp-implementation-plan.md)

## Decided Direction

- Python-only MCP server for MVP
- Headless deterministic inspection as the required first mode
- `klayout.db` for layout database access
- `klayout.lay.LayoutView` for deterministic rendering
- `klayout -b -r` reserved for running existing DRC decks in batch mode
- No geometry editing in MVP

## What "Done" Means For Handoff

Another agent should be able to start from zero repo context and know:

- which files to create first
- which tool names and schemas are fixed
- how sessions, artifacts, and errors behave
- which tests to write
- which milestone order to follow

Those details live in the contract and implementation plan, not only in the design brief.
