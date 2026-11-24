"""Every request the operations make names a real procedure with its real arguments.

The check reads the source: each ``Request("name", {...})`` is compared with the
generated ``Procedure``. A dict held in a variable is followed to its assignment
in the same function, including later ``variable["key"] = ...`` additions.
"""

import ast
from pathlib import Path

import pytest

from libvirtpy.rpc.protocol.procedures import PROCEDURES

CLIENT = Path(__file__).resolve().parents[2] / "src" / "libvirtpy" / "client"
BY_NAME = {procedure.name: procedure for procedure in PROCEDURES.values()}


def requests_in(path: Path) -> list[tuple[str, str, list[str] | None]]:
    """Find the requests of a module: (function, procedure, argument names)."""
    found: list[tuple[str, str, list[str] | None]] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef):
            continue
        found.extend(
            _describe(function, call)
            for call in ast.walk(function)
            if _is_request(call)
        )
    return [item for item in found if item[1]]


def _is_request(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Request"
        and bool(node.args)
    )


def _describe(
    function: ast.FunctionDef, call: ast.AST
) -> tuple[str, str, list[str] | None]:
    assert isinstance(call, ast.Call)
    name = call.args[0]
    procedure = name.value if isinstance(name, ast.Constant) else ""
    return function.name, str(procedure), _keys(function, call.args[1:])


def _keys(function: ast.FunctionDef, arguments: list[ast.expr]) -> list[str] | None:
    if not arguments:
        return []
    argument = arguments[0]
    if isinstance(argument, ast.Dict):
        return _dict_keys(argument)
    if isinstance(argument, ast.Name):
        return _variable_keys(function, argument.id)
    return None


def _dict_keys(node: ast.Dict) -> list[str]:
    return [str(key.value) for key in node.keys if isinstance(key, ast.Constant)]


def _variable_keys(function: ast.FunctionDef, name: str) -> list[str] | None:
    keys: list[str] = []
    assigned = False
    for node in ast.walk(function):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)):
            continue
        if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            keys += _dict_keys(node.value)
            assigned = True
    return keys if assigned else None


MODULES = [
    *sorted((CLIENT / "operations").glob("[!_]*.py")),
    CLIENT / "references.py",
    CLIENT / "operations" / "_common.py",
]
CASES = [
    case for module in MODULES for case in requests_in(module) if case[2] is not None
]


def test_the_check_sees_most_requests() -> None:
    assert len(CASES) > 75


@pytest.mark.parametrize(
    ("function", "procedure", "keys"), CASES, ids=lambda value: str(value)[:40]
)
def test_request_matches_the_procedure(
    function: str, procedure: str, keys: list[str]
) -> None:
    real = BY_NAME.get(procedure)

    assert real is not None, f"{function}: {procedure} is not a libvirt procedure"
    expected = sorted(name for name, _ in real.args.xdr_fields) if real.args else []
    assert sorted(keys) == expected, f"{function}: {procedure}"
