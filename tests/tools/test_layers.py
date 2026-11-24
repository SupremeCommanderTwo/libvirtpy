"""The layers of ``libvirtpy`` import each other in one direction only."""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "libvirtpy"

# layer -> the layers it must not import (``errors`` is shared by all of them)
FORBIDDEN = {
    "xml": ("libvirtpy.rpc", "libvirtpy.client"),
    "rpc": ("libvirtpy.xml", "libvirtpy.client"),
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_does_not_import_the_layers_it_must_not_know(layer: str) -> None:
    violations = [
        f"{path.relative_to(PACKAGE)} imports {module}"
        for path in sorted((PACKAGE / layer).rglob("*.py"))
        for module in imported_modules(path)
        if module.startswith(FORBIDDEN[layer])
    ]

    assert violations == []
