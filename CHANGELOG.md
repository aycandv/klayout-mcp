# Changelog

All notable changes to this project are documented in this file.

The format follows Keep a Changelog, and versions use SemVer in PEP 440 form.

## [0.2.0](https://github.com/aycandv/klayout-mcp/compare/klayout-mcp-v0.1.1...klayout-mcp-v0.2.0) (2026-03-06)


### Features

* add batch drc execution and marker extraction ([8ba3f96](https://github.com/aycandv/klayout-mcp/commit/8ba3f9669c6778ba91ddba4c02c02b78c9738aa3))
* add bounded region queries ([d1639c2](https://github.com/aycandv/klayout-mcp/commit/d1639c23b69fc033fa54f7f19fa19b6ede39c7f4))
* add cell hierarchy inspection tools ([19ddb9a](https://github.com/aycandv/klayout-mcp/commit/19ddb9a8f2938e6cb1780b3f8b3035f2c471a942))
* add config and session storage ([71776ff](https://github.com/aycandv/klayout-mcp/commit/71776ff335798b670f59ba5ad53b748137c68603))
* add deterministic rendering tools ([4fe7657](https://github.com/aycandv/klayout-mcp/commit/4fe7657c6a4fc7e8f66703bde8a89c8783750c07))
* add geometry measurement tools ([3b0e7c2](https://github.com/aycandv/klayout-mcp/commit/3b0e7c28e43a6ac75f2b449f3263238be544b6ee))
* add layout open and layer inspection tools ([485dab5](https://github.com/aycandv/klayout-mcp/commit/485dab59b8e6fb8265d1c2d888c0f24027c6da1e))
* remove path allowlist restrictions ([b2dedf1](https://github.com/aycandv/klayout-mcp/commit/b2dedf1c875d591c08cdd00b133eb81ad8e892f0))
* remove path allowlist restrictions ([f7dc42e](https://github.com/aycandv/klayout-mcp/commit/f7dc42e9018d57fba4b8a1a4a9ef1822c95d57a2))


### Bug Fixes

* checkout repo before creating github release ([e83606b](https://github.com/aycandv/klayout-mcp/commit/e83606b9c33c057be3aa83b42091259fd1ca4fc2))
* remove server entrypoint warning ([e910c4c](https://github.com/aycandv/klayout-mcp/commit/e910c4c3090a1816d382be343660c5957d5c1613))


### Documentation

* add contributor guide ([218942b](https://github.com/aycandv/klayout-mcp/commit/218942b6ffefdf86833bf412cf9c908e750b43f0))
* add klayout mcp handoff ([04acf93](https://github.com/aycandv/klayout-mcp/commit/04acf931a6476cb9aa2bc14e55af8db8c6a60238))
* refresh repository README ([c5387b0](https://github.com/aycandv/klayout-mcp/commit/c5387b0a7cc1e25fe4ea721917dd5806758b192a))
* simplify installation guide ([f9aa793](https://github.com/aycandv/klayout-mcp/commit/f9aa793b104eb898f530c71960d3cc5a2df67e15))

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
