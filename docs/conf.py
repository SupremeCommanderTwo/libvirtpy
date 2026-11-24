"""Sphinx configuration of the libvirtpy documentation."""

from importlib.metadata import version as installed_version
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sphinx.application import Sphinx

project = "libvirtpy"
author = "SupremeCommanderTwo"
copyright = "2026, SupremeCommanderTwo"  # noqa: A001  (Sphinx reads this name)
release = installed_version("libvirtpy")
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "myst_parser",
]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
exclude_patterns = ["_build"]
myst_heading_anchors = 3

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {"members": True, "show-inheritance": True}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest", None),
}

html_theme = "furo"
html_title = "libvirtpy"
html_theme_options = {
    "source_repository": "https://github.com/SupremeCommanderTwo/libvirtpy/",
    "source_branch": "master",
    "source_directory": "docs/",
}


documented: set[int] = set()


def skip_repeats(
    app: object, what: str, name: str, obj: object, skip: bool, options: object
) -> bool:
    """Document a class once, even if several packages re-export it.

    :param app: the Sphinx application (unused).
    :param what: the kind of the parent object (module, class, ...).
    :param name: the member's name.
    :param obj: the member.
    :param skip: whether autodoc would skip it.
    :param options: the autodoc options (unused).
    :returns: ``True`` to skip a class that an earlier page documented.
    """
    if skip or what != "module" or not isinstance(obj, type):
        return skip
    if id(obj) in documented:
        return True
    documented.add(id(obj))
    return False


def setup(app: Sphinx) -> None:
    """Connect the hook.

    :param app: the Sphinx application.
    """
    app.connect("autodoc-skip-member", skip_repeats)
