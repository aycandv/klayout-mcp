# Contributing

This project uses a branch-and-PR workflow with enforced CI on `main`.

## Development Setup

Requirements:

- Python 3.11+
- `uv`
- KLayout installed locally

Set up a local development environment:

```bash
uv venv --python python3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
uv run pre-commit install --hook-type commit-msg --install-hooks
```

Useful local commands:

```bash
./.venv/bin/python -m ruff check .
./.venv/bin/python -m pytest -q
```

## Branch Workflow

- Do not develop directly on `main`.
- Create feature branches with the `feat/` naming pattern.
- Open a pull request for all normal code changes.
- Wait for GitHub Actions `CI` to pass before merging.
- `main` requires pull requests and the `checks` status check.

Example:

```bash
git checkout -b feat/add-layer-filter
git push -u origin feat/add-layer-filter
```

## Commit Conventions

This repository uses Conventional Commits.

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

Examples:

```text
feat: add layer filter option
fix: normalize marker crop paths
docs: clarify Cursor MCP setup
```

Commit messages are checked locally with `pre-commit` and in GitHub Actions.

## Pull Requests

Before opening a pull request:

1. Run `./.venv/bin/python -m ruff check .`
2. Run `./.venv/bin/python -m pytest -q`
3. Review your diff for unrelated changes
4. Push your branch and open a PR against `main`

PRs should include:

- a short summary of the change
- verification notes
- any follow-up work or limitations

## Code Comments

Use comments sparingly and only when they add information the code does not already say clearly.

- Keep module docstrings on public modules.
- Use Google-style docstrings for classes and functions in `src/klayout_mcp`, including internal helpers.
- Add inline comments only for intent, invariants, KLayout quirks, unit conversions, or error-handling rationale.
- Do not add comments that restate obvious code line by line.
- Prefer short comments near the relevant code over long explanatory blocks.

## Releases

Human-readable release notes live in [CHANGELOG.md](CHANGELOG.md).

Normal release flow:

1. Merge Conventional Commits to `main`
2. Wait for `release-please` to open or update the release PR
3. Review and merge the release PR
4. The merge creates the version bump, tag, GitHub release, and PyPI publish automatically

For protected branches, configure a `RELEASE_PLEASE_TOKEN` repository secret so the release PR triggers normal pull request CI. Without that token, `release-please` falls back to `github.token`, which may not run PR workflows.

The manual [release.yml](.github/workflows/release.yml) workflow remains available for TestPyPI validation and recovery publishing.

## Project-Specific Notes

- Keep MCP tool names and error codes aligned with the contract in [2026-03-05-klayout-observer-mcp-contract.md](docs/specs/2026-03-05-klayout-observer-mcp-contract.md)
- Keep responses machine-readable and deterministic
- Do not add GUI editing behavior unless explicitly requested
