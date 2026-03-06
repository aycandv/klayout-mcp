from pathlib import Path
import tomllib


def test_precommit_config_installs_commit_msg_hook():
    text = Path(".pre-commit-config.yaml").read_text()
    assert "default_install_hook_types:" in text
    assert "- commit-msg" in text
    assert "repo: https://github.com/compilerla/conventional-pre-commit" in text
    assert "id: conventional-pre-commit" in text
    assert "stages: [commit-msg]" in text


def test_ci_workflow_validates_commit_messages():
    text = Path(".github/workflows/ci.yml").read_text()
    assert "fetch-depth: 0" in text
    assert "Validate commit messages" in text
    assert "uvx conventional-pre-commit" in text


def test_project_dev_dependencies_include_pre_commit():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]
    assert any(dependency.startswith("pre-commit") for dependency in dev_dependencies)
