import ast
from pathlib import Path


SRC_ROOT = Path("src/klayout_mcp")


def _all_definition_nodes(tree: ast.AST):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield (node.name, node)
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        yield (f"{node.name}.{child.name}", child)


def _missing_docstrings() -> list[str]:
    missing: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for name, node in _all_definition_nodes(tree):
            if ast.get_docstring(node) is None:
                missing.append(f"{path}:{name}")
    return missing


def _google_style_docstring_issues() -> list[str]:
    issues: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for name, node in _all_definition_nodes(tree):
            docstring = ast.get_docstring(node)
            if docstring is None:
                continue
            summary = docstring.strip().splitlines()[0]
            if summary.endswith(".") is False:
                issues.append(f"{path}:{name}:summary-must-end-with-period")
            if summary[:1].islower():
                issues.append(f"{path}:{name}:summary-must-start-with-capital")
    return issues


def test_public_python_api_has_docstrings():
    assert _missing_docstrings() == []


def test_public_python_api_uses_basic_google_style_docstrings():
    assert _google_style_docstring_issues() == []
