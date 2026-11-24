"""Rewrite a package's ``__init__.py`` so it re-exports every module's ``__all__``.

Explicit imports keep ``from libvirtpy.xml.domain import Disk`` working without
star imports. Run it after adding a public class to a module.

Usage: ``python tools/gen_exports.py libvirtpy.xml.domain [--extra module ...]``

Every module of the package that defines ``__all__`` is included; ``--extra``
adds modules from elsewhere (for example ``libvirtpy.xml._shared.metadata``), or
only some of their names (``libvirtpy.xml._shared.storage:StorageSecret,Permissions``).
The modules are read as text, not imported, so a broken ``__init__.py`` does
not get in the way.
"""

import argparse
import ast
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent / "src"


def module_file(module_name: str) -> Path:
    """Return the source file of a module of the package.

    :param module_name: the dotted module name, e.g. ``libvirtpy.xml.domain.os``.
    :returns: the path of its ``.py`` file under ``src/``.
    """
    return SOURCE_ROOT.joinpath(*module_name.split(".")).with_suffix(".py")


def read_all(module_name: str) -> list[str] | None:
    """Return the names in the module's ``__all__``, or ``None`` if it has none.

    :param module_name: the dotted name of the module to read (as text, not imported).
    :returns: the names listed in ``__all__``, or ``None`` without one.
    """
    tree = ast.parse(module_file(module_name).read_text(encoding="utf-8"))

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            return [
                str(ast.literal_eval(element))
                for element in ast.iter_child_nodes(node.value)
                if isinstance(element, ast.Constant)
            ]

    return None


def package_modules(package_name: str) -> list[str]:
    """Return the plain modules of the package that define ``__all__``.

    :param package_name: the dotted name of the package.
    :returns: the dotted names of its modules, sorted.
    """
    package_dir = SOURCE_ROOT.joinpath(*package_name.split("."))
    names = []
    for path in sorted(package_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        module_name = f"{package_name}.{path.stem}"
        if read_all(module_name) is not None:
            names.append(module_name)
    return names


def names_of(entry: str) -> tuple[str, list[str]]:
    """Split ``module`` or ``module:Name,Name`` into the module and its names.

    :param entry: a module name, optionally followed by ``:`` and the names to take.
    :returns: the module name and the names to export (all of ``__all__`` if none
        were given).
    :raises SystemExit: if a requested name is not in the module's ``__all__``.
    """
    module_name, _, wanted = entry.partition(":")
    available = read_all(module_name) or []

    if not wanted:
        return module_name, available

    names = wanted.split(",")
    missing = [name for name in names if name not in available]
    if missing:
        raise SystemExit(f"{module_name} does not export {missing}")

    return module_name, names


def render(docstring: str, modules: list[str]) -> str:
    """Build the text of a package ``__init__.py``.

    :param docstring: the package docstring to keep.
    :param modules: the modules to re-export, as accepted by ``names_of``.
    :returns: the file content.
    """
    lines = [f'"""{docstring}"""', ""]
    exported: set[str] = set()

    for entry in modules:
        module_name, names = names_of(entry)
        # A name that several modules list (a re-export) is imported once.
        public = sorted(name for name in names if name not in exported)
        exported.update(public)
        if not public:
            continue

        lines.append(f"from {module_name} import (")
        lines.extend(f"    {name}," for name in public)
        lines.append(")")

    lines.extend(["", "__all__ = ["])
    lines.extend(f'    "{name}",' for name in sorted(exported))
    lines.extend(["]", ""])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package")
    parser.add_argument("--extra", nargs="*", default=[])
    arguments = parser.parse_args()

    init_file = SOURCE_ROOT.joinpath(*arguments.package.split("."), "__init__.py")
    existing = ast.get_docstring(ast.parse(init_file.read_text(encoding="utf-8")))
    docstring = (existing or arguments.package).splitlines()[0]

    modules = package_modules(arguments.package) + arguments.extra
    init_file.write_text(render(docstring, modules), encoding="utf-8")
    print(f"wrote {init_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
