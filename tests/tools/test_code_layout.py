"""Functions of ``src/`` and ``tools/`` have no long runs without a blank line."""

import ast
from collections.abc import Iterator
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIRECTORIES = ("src", "tools")
MAX_STATEMENTS_WITHOUT_BLANK_LINE = 5
FUNCTION_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)
# Test doubles shipped with the package follow the exemptions of tests.
TEST_DOUBLE_PACKAGES = ("testing",)
SIMPLE_BODY_ATTRIBUTES = ("body", "orelse", "finalbody")


def test_no_long_runs_of_statements_without_a_blank_line() -> None:
    too_long = [
        f"{path.relative_to(REPOSITORY_ROOT)}:{run[0].lineno} {len(run)} statements"
        for path in _source_files()
        for run in _runs(path.read_text(encoding="utf-8"))
        if len(run) > MAX_STATEMENTS_WITHOUT_BLANK_LINE
    ]

    assert not too_long, "split these with blank lines:\n" + "\n".join(too_long)


def test_the_check_finds_a_long_run() -> None:
    source = "def f():\n" + "".join(f"    x{n} = {n}\n" for n in range(7))

    runs = list(_runs(source))

    assert [len(run) for run in runs] == [7]


def test_a_blank_line_ends_a_run() -> None:
    source = "def f():\n    a = 1\n    b = 2\n\n    c = 3\n    d = 4\n"

    runs = list(_runs(source))

    assert [len(run) for run in runs] == [2, 2]


def _source_files() -> list[Path]:
    return sorted(
        path
        for directory in SOURCE_DIRECTORIES
        for path in (REPOSITORY_ROOT / directory).rglob("*.py")
        if not set(path.parts) & set(TEST_DOUBLE_PACKAGES)
    )


def _runs(source: str) -> Iterator[list[ast.stmt]]:
    """Yield the runs of statements, in function bodies, with no blank line between."""
    lines = source.splitlines()
    for body in _function_bodies(ast.parse(source)):
        run: list[ast.stmt] = []
        for statement in _without_docstring(body):
            previous_line = lines[statement.lineno - 2]
            continues_run = bool(run) and previous_line.strip() != ""
            if not continues_run and run:
                yield run
                run = []
            run.append(statement)
        if run:
            yield run


def _function_bodies(tree: ast.AST) -> Iterator[list[ast.stmt]]:
    """Yield every statement list inside a function: its body and nested blocks."""
    for function in ast.walk(tree):
        if not isinstance(function, FUNCTION_TYPES):
            continue
        yield function.body
        for node in ast.walk(function):
            for attribute in SIMPLE_BODY_ATTRIBUTES:
                block = getattr(node, attribute, None)
                if isinstance(block, list) and block and block is not function.body:
                    yield [
                        statement
                        for statement in block
                        if isinstance(statement, ast.stmt)
                    ]


def _without_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    first = body[0]
    is_docstring = (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    )
    return body[1:] if is_docstring else body
