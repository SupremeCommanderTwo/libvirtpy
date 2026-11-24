"""Every function of ``src/`` and ``tools/`` documents each of its parameters."""

import ast
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIRECTORIES = ("src", "tools")
FUNCTION_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)
# Test doubles shipped with the package follow the exemptions of tests.
TEST_DOUBLE_PACKAGES = ("testing",)


def test_every_parameter_is_documented() -> None:
    missing = [
        f"{path.relative_to(REPOSITORY_ROOT)}:{function.lineno} {function.name}: {name}"
        for path in _source_files()
        for function in _functions(ast.parse(path.read_text(encoding="utf-8")))
        for name in _undocumented_parameters(function)
    ]

    assert not missing, "missing ':param name:' lines:\n" + "\n".join(missing)


@pytest.mark.parametrize(
    ("source", "undocumented"),
    [
        pytest.param(
            "def f(a, b):\n    '''Text.\n\n    :param a: x.\n    '''\n", ["b"]
        ),
        pytest.param("def f(a):\n    '''Text.'''\n", ["a"]),
        pytest.param("def f(a):\n    pass\n", ["a"], id="no-docstring"),
        pytest.param(
            "def f(self, *, a, **kw):\n"
            "    '''T.\n\n    :param a: x.\n    :param kw: y.\n    '''\n",
            [],
            id="all-documented",
        ),
        pytest.param("def f():\n    '''Text.'''\n", [], id="no-parameters"),
    ],
)
def test_the_check_finds_undocumented_parameters(
    source: str, undocumented: list[str]
) -> None:
    (function,) = _functions(ast.parse(source))

    assert _undocumented_parameters(function) == undocumented


def _source_files() -> list[Path]:
    return sorted(
        path
        for directory in SOURCE_DIRECTORIES
        for path in (REPOSITORY_ROOT / directory).rglob("*.py")
        if not set(path.parts) & set(TEST_DOUBLE_PACKAGES)
    )


def _functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in ast.walk(tree) if isinstance(node, FUNCTION_TYPES)]


def _undocumented_parameters(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    arguments = function.args
    parameters = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
    names = [argument.arg for argument in parameters]
    names += [
        argument.arg for argument in (arguments.vararg, arguments.kwarg) if argument
    ]

    documentation = ast.get_docstring(function) or ""
    return [
        name
        for name in names
        if name not in ("self", "cls") and f":param {name}:" not in documentation
    ]
