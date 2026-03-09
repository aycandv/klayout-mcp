from pathlib import Path
import tomllib


def test_project_declares_docs_dependencies_for_local_and_rtd_builds():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    docs_dependencies = pyproject["project"]["optional-dependencies"]["docs"]

    assert any(dependency.startswith("mkdocs") for dependency in docs_dependencies)
    assert any("mkdocs-material" in dependency for dependency in docs_dependencies)


def test_readthedocs_and_mkdocs_configs_exist():
    readthedocs = Path(".readthedocs.yaml")
    mkdocs = Path("mkdocs.yml")

    assert readthedocs.exists()
    assert mkdocs.exists()

    readthedocs_text = readthedocs.read_text()
    mkdocs_text = mkdocs.read_text()

    assert "version: 2" in readthedocs_text
    assert "mkdocs:" in readthedocs_text
    assert "mkdocs.yml" in readthedocs_text
    assert "extra_requirements:" in readthedocs_text
    assert "docs" in readthedocs_text
    assert "site_name:" in mkdocs_text
    assert "nav:" in mkdocs_text


def test_mkdocs_theme_defaults_to_dark_mode_with_palette_toggle():
    mkdocs_text = Path("mkdocs.yml").read_text()

    assert "theme:" in mkdocs_text
    assert "palette:" in mkdocs_text
    assert '- scheme: slate' in mkdocs_text
    assert "name: Switch to light mode" in mkdocs_text
    assert '- scheme: default' in mkdocs_text
    assert "name: Switch to dark mode" in mkdocs_text


def test_docs_site_has_expected_core_pages():
    expected_pages = [
        Path("docs/index.md"),
        Path("docs/getting-started.md"),
        Path("docs/clients.md"),
        Path("docs/reference.md"),
        Path("docs/development.md"),
    ]

    for page in expected_pages:
        assert page.exists(), f"Missing docs page: {page}"
