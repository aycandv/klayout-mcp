from pathlib import Path
import json
import tomllib


def _workflow_text(name: str) -> str:
    return Path(".github/workflows", name).read_text()


SELF_HOSTED_RUNNER = "runs-on: [self-hosted, linux, ARM64, kevipi]"


def test_ci_workflow_runs_lint_tests_and_build_on_push_and_pr():
    text = _workflow_text("ci.yml")
    assert "pull_request:" in text
    assert "push:" in text
    assert "uv sync --python 3.12 --extra dev" in text
    assert "uv run ruff check ." in text
    assert "uv run pytest -q" in text
    assert "uv run --extra docs mkdocs build --strict" in text
    assert "uv build" in text
    assert "uvx twine check dist/*" in text


def test_all_workflows_target_the_kevipi_self_hosted_runner():
    for workflow_name in ("ci.yml", "release-please.yml", "release.yml"):
        text = _workflow_text(workflow_name)
        assert SELF_HOSTED_RUNNER in text
        assert "ubuntu-latest" not in text


def test_python_workflows_use_uv_managed_python_on_kevipi():
    for workflow_name in ("ci.yml", "release.yml"):
        text = _workflow_text(workflow_name)
        assert "astral-sh/setup-uv@v7" in text
        assert "uv python install 3.12" in text
        assert "uv sync --python 3.12 --extra dev" in text
        assert "actions/setup-python" not in text


def test_release_workflow_uses_separate_build_and_trusted_publish_jobs():
    text = _workflow_text("release.yml")
    assert "workflow_dispatch:" in text
    assert "release:" in text
    assert "published" in text
    assert "uv sync --python 3.12 --extra dev" in text
    assert "actions/upload-artifact" in text
    assert "actions/download-artifact" in text
    assert "id-token: write" in text
    assert "environment:" in text
    assert "pypa/gh-action-pypi-publish@release/v1" in text


def test_release_please_workflow_creates_release_prs_and_publishes_to_pypi():
    text = _workflow_text("release-please.yml")
    assert "push:" in text
    assert "branches:" in text
    assert "main" in text
    assert "googleapis/release-please-action@v4" in text
    assert "RELEASE_PLEASE_TOKEN" in text
    assert "release_created" not in text
    assert "pypa/gh-action-pypi-publish@release/v1" not in text


def test_release_please_config_matches_current_python_package_version():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    version = pyproject["project"]["version"]

    config = json.loads(Path("release-please-config.json").read_text())
    manifest = json.loads(Path(".release-please-manifest.json").read_text())

    assert config["packages"]["."]["release-type"] == "python"
    assert config["packages"]["."]["changelog-path"] == "CHANGELOG.md"
    assert "package-name" not in config["packages"]["."]
    assert manifest["."] == version


def test_tag_driven_github_release_workflow_is_removed():
    assert not Path(".github/workflows/github-release.yml").exists()
