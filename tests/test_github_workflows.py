from pathlib import Path


def _workflow_text(name: str) -> str:
    return Path(".github/workflows", name).read_text()


def test_ci_workflow_runs_lint_tests_and_build_on_push_and_pr():
    text = _workflow_text("ci.yml")
    assert "pull_request:" in text
    assert "push:" in text
    assert "uv sync --extra dev" in text
    assert "uv run ruff check ." in text
    assert "uv run pytest -q" in text
    assert "uv build" in text
    assert "uvx twine check dist/*" in text


def test_release_workflow_uses_separate_build_and_trusted_publish_jobs():
    text = _workflow_text("release.yml")
    assert "workflow_dispatch:" in text
    assert "uv sync --extra dev" in text
    assert "actions/upload-artifact" in text
    assert "actions/download-artifact" in text
    assert "id-token: write" in text
    assert "environment:" in text
    assert "pypa/gh-action-pypi-publish@release/v1" in text


def test_github_release_workflow_creates_release_from_version_tags():
    text = _workflow_text("github-release.yml")
    assert "push:" in text
    assert '      - "v*"' in text
    assert "contents: write" in text
    assert 'gh release create "$GITHUB_REF_NAME"' in text
    assert "--verify-tag" in text
    assert "--generate-notes" in text
