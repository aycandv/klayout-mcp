# Changelog

All notable changes to this project are documented in this file.

The format follows Keep a Changelog, and versions use SemVer in PEP 440 form.

## [0.2.2](https://github.com/aycandv/klayout-mcp/compare/v0.2.1...v0.2.2) (2026-03-09)


### Bug Fixes

* pin klayout to 0.30.6 ([80e3d85](https://github.com/aycandv/klayout-mcp/commit/80e3d85544dfa54bbb22e17b4949aee5d64efe95))
* render actual geometry in render_view ([6fa239c](https://github.com/aycandv/klayout-mcp/commit/6fa239c07b07ed7de1ba708b50aebabe829ed675))
* render actual geometry in render_view ([5193b91](https://github.com/aycandv/klayout-mcp/commit/5193b9197e61c749aad0db3424f8c0626b5cdec1))

## [0.2.1](https://github.com/aycandv/klayout-mcp/compare/v0.2.0...v0.2.1) (2026-03-07)


### Documentation

* default docs site to dark mode ([243e4c5](https://github.com/aycandv/klayout-mcp/commit/243e4c53bc546475168797e812064a7f548a6ae6))
* default docs site to dark mode ([53c1a2c](https://github.com/aycandv/klayout-mcp/commit/53c1a2cd0b676945dea15168ff6655cbeb77bdb9))

## [0.2.0](https://github.com/aycandv/klayout-mcp/compare/v0.1.6...v0.2.0) (2026-03-06)


### Features

* add waveguide analysis tool ([1f9fc81](https://github.com/aycandv/klayout-mcp/commit/1f9fc81e1df603c9d94a17f422915ae2b9cbb823))
* add waveguide analysis tool ([480da58](https://github.com/aycandv/klayout-mcp/commit/480da58414695f1cace85f05a005e29fb6bfcc45))


### Bug Fixes

* classify Manhattan bends as axis aligned ([f5f4d3c](https://github.com/aycandv/klayout-mcp/commit/f5f4d3c816bab5cd448a30d6aec63fa3fd6a7d3b))

## [0.1.6](https://github.com/aycandv/klayout-mcp/compare/v0.1.5...v0.1.6) (2026-03-06)


### Documentation

* add status badges ([fb39ff9](https://github.com/aycandv/klayout-mcp/commit/fb39ff9eb6487bb110ef76ea5a1bcf6fa643ef85))

## [0.1.5](https://github.com/aycandv/klayout-mcp/compare/v0.1.4...v0.1.5) (2026-03-06)


### Documentation

* add Read the Docs site ([11570b6](https://github.com/aycandv/klayout-mcp/commit/11570b6e4da1f49c3443f13ec35c2b1e1f68d357))
* add readthedocs site ([9fd1708](https://github.com/aycandv/klayout-mcp/commit/9fd1708e32a19adb19e19cad80166f8a0f84a0ed))

## [0.1.4](https://github.com/aycandv/klayout-mcp/compare/v0.1.3...v0.1.4) (2026-03-06)


### Documentation

* enforce google-style docstrings ([7579f4f](https://github.com/aycandv/klayout-mcp/commit/7579f4fbdb584e58ffacc2266dc8e44f7ff62c0c))
* enforce google-style docstrings ([8e8cf06](https://github.com/aycandv/klayout-mcp/commit/8e8cf06e3c821cd79f3996671d9d4c442e526c36))

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
