"""Every operation runs against the real protocol structures.

Each public operation is called with sample arguments (made from its signature)
through a daemon that checks the request against the generated argument struct
and answers with a sample of the real return struct. Nothing here shows that the
daemon would *do* the right thing; it shows that the request is well-formed and
the operation understands the shape of the reply.
"""

import collections.abc
import inspect
import types as pytypes
import typing
import uuid
from collections.abc import Callable
from typing import Any

import pytest

from libvirtpy.client import operations
from libvirtpy.client._runner import run_sync
from tests.helpers.synthetic_daemon import SyntheticDaemon

OPERATIONS = sorted(
    (
        (name, function)
        for name, function in inspect.getmembers(operations, inspect.isfunction)
        if not name.startswith("_")
    ),
    key=lambda item: item[0],
)
UUID_TEXT = str(uuid.UUID(int=1))


def argument_for(name: str, hint: Any) -> Any:
    """Make a sample argument for a required parameter.

    :param name: the parameter name.
    :param hint: its resolved annotation.
    :returns: a value of that type.
    """
    if name in ("secret", "port"):
        return UUID_TEXT
    hint = unwrap_alias(hint)
    options = typing.get_args(hint) if _is_union(hint) else (hint,)
    if str in options or any(o is uuid.UUID for o in options):
        return "ab"
    return _plain_argument(options[0])


def unwrap_alias(hint: Any) -> Any:
    """Replace a ``type X = ...`` alias (``DomainRef``) by what it stands for."""
    while isinstance(hint, typing.TypeAliasType):
        hint = hint.__value__
    return hint


def _is_union(hint: Any) -> bool:
    return (
        isinstance(hint, pytypes.UnionType) or typing.get_origin(hint) is typing.Union
    )


def _plain_argument(hint: Any) -> Any:
    origin = typing.get_origin(hint) or hint
    if origin in (list, collections.abc.Iterable):
        item_hints = typing.get_args(hint)
        return [_plain_argument(item_hints[0])] if item_hints else []
    if origin is typing.Literal:
        return typing.get_args(hint)[0]
    samples = {int: 1, float: 1.0, bool: True, bytes: b"ab", str: "ab", dict: {}}
    if origin in samples:
        return samples[origin]
    raise TypeError(f"no sample for {hint!r}")


def sample_call(function: Callable[..., Any]) -> dict[str, Any]:
    """Make the arguments for a call of ``function`` (required ones only).

    :param function: an operation.
    :returns: the keyword arguments.
    """
    hints = typing.get_type_hints(function)
    return {
        name: argument_for(name, hints[name])
        for name, parameter in inspect.signature(function).parameters.items()
        if parameter.default is inspect.Parameter.empty
    }


def test_the_harness_sees_the_operations() -> None:
    assert len(OPERATIONS) >= 75


@pytest.mark.parametrize(
    ("name", "function"), OPERATIONS, ids=lambda v: getattr(v, "__name__", str(v))
)
def test_operation_speaks_the_real_protocol(
    name: str, function: Callable[..., Any]
) -> None:
    daemon = SyntheticDaemon()

    run_sync(function(**sample_call(function)), daemon.call)

    assert daemon.requests, f"{name} sent nothing"
