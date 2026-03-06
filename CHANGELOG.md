# Changelog

All notable changes to this project are documented in this file.

The format follows Keep a Changelog, and versions use SemVer in PEP 440 form.

## [0.1.3](https://github.com/aycandv/klayout-mcp/compare/v0.1.2...v0.1.3) (2026-03-06)


### Bug Fixes

* publish releases from trusted workflow ([559b702](https://github.com/aycandv/klayout-mcp/commit/559b702904536f75a6d156526cac1aea5e3f20b0))
* publish releases from trusted workflow ([b5328f7](https://github.com/aycandv/klayout-mcp/commit/b5328f7c86e27691e869eaf87550a2263f8f0319))

## [0.1.2](https://github.com/aycandv/klayout-mcp/compare/v0.1.1...v0.1.2) (2026-03-06)


### Bug Fixes

* align release-please with v-tag history ([1901c7c](https://github.com/aycandv/klayout-mcp/commit/1901c7c85f7a5b68f3610c360df6f6ee77cb118f))
* align release-please with v-tag history ([d4f215e](https://github.com/aycandv/klayout-mcp/commit/d4f215e54da54bbd7dca133e61e331003c98f8e5))

## [Unreleased]

### Changed

- Added `release-please` automation for version selection, release PRs, tagging, GitHub releases, and PyPI publishing

## [0.1.1] - 2026-03-06

### Changed

- Removed layout and DRC path allowlist restrictions from the runtime and contract
- Simplified MCP client setup by removing the allowlist environment variables from docs and examples

## [0.1.0] - 2026-03-06

### Added

- Initial public release of `klayout-mcp`
- Read-only MCP tools for layout loading, layer inspection, cell hierarchy, region queries, geometry measurement, deterministic rendering, batch DRC, and marker extraction
- Structured error objects with stable error codes
- Allowlisted layout and DRC roots
- Published package entry point: `klayout-mcp`
- Example MCP client configs for Codex, Claude Code, Cursor, and OpenCode
- GitHub Actions CI, Trusted Publishing release workflow, and Conventional Commits enforcement
