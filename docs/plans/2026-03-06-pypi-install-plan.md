# PyPI Install Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `klayout-mcp` easy to install as a published Python package with a real console script that MCP clients can launch directly.

**Architecture:** Keep the existing `klayout_mcp.server:main` runtime entrypoint and expose it as an installable console script through packaging metadata. Treat PyPI-readiness as a packaging and documentation change: verify the script is declared, verify it resolves in an installed environment, and document the published `uvx` path separately from the source-checkout fallback.

**Tech Stack:** Python 3.11+, setuptools, `uv`, `pytest`, `tomllib`

---

### Task 1: Prove the console script is missing

**Files:**
- Create: `tests/test_packaging_metadata.py`
- Modify: `pyproject.toml`

**Step 1: Write the failing test**

```python
import tomllib
from pathlib import Path


def test_project_declares_klayout_mcp_console_script():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    scripts = pyproject["project"]["scripts"]
    assert scripts["klayout-mcp"] == "klayout_mcp.server:main"
```

**Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/test_packaging_metadata.py -q`
Expected: FAIL because `project.scripts` is not declared yet.

### Task 2: Add publishable package metadata

**Files:**
- Modify: `pyproject.toml`

**Step 1: Write minimal implementation**

Add:
- `project.scripts.klayout-mcp = "klayout_mcp.server:main"`
- package metadata needed for a normal PyPI release, such as `license`, `authors`, `keywords`, and `urls`

**Step 2: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_packaging_metadata.py -q`
Expected: PASS

### Task 3: Prove the installed command resolves

**Files:**
- Modify: `tests/test_packaging_metadata.py`

**Step 1: Write the failing integration test**

Create a temporary virtual environment, install the project, and assert the `klayout-mcp` launcher exists in the venv `bin` directory.

**Step 2: Run test to verify it fails or exposes packaging gaps**

Run: `./.venv/bin/python -m pytest tests/test_packaging_metadata.py::test_installed_package_exposes_klayout_mcp_launcher -q`
Expected: FAIL until packaging metadata is complete.

**Step 3: Adjust packaging only as needed**

Keep the runtime entrypoint at `klayout_mcp.server:main`. Do not add a second CLI surface unless the test proves it is necessary.

**Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/test_packaging_metadata.py -q`
Expected: PASS

### Task 4: Update user install docs

**Files:**
- Modify: `README.md`
- Modify: `examples/mcp/README.md`
- Modify: `examples/mcp/codex.config.toml`
- Modify: `examples/mcp/claude-code.mcp.json`
- Modify: `examples/mcp/cursor.mcp.json`
- Modify: `examples/mcp/opencode.json`

**Step 1: Update docs for the published path**

Document the published install and launch flow first:
- `uvx klayout-mcp`
- `uv tool install klayout-mcp`

Keep the source-checkout `uv --directory ... run ...` path as the fallback for contributors and unreleased builds.

**Step 2: Verify docs formatting**

Run: `git diff --check -- README.md examples/mcp`
Expected: PASS

### Task 5: Verify end-to-end packaging behavior

**Files:**
- Modify: none

**Step 1: Run the focused tests**

Run: `./.venv/bin/python -m pytest tests/test_packaging_metadata.py -q`
Expected: PASS

**Step 2: Verify the installed command starts**

Run a temporary installed command through `uv` and confirm it starts the stdio server process cleanly before terminating it.

**Step 3: Re-run repo verification**

Run:
- `./.venv/bin/python -m pytest tests/test_packaging_metadata.py tests/test_server_entrypoint.py -q`
- `git diff --check -- README.md examples/mcp pyproject.toml`

Expected: PASS
