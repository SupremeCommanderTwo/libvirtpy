"""Typed parameters: dicts in Python, typed lists on the wire."""

import pytest

from libvirtpy.rpc.protocol import types
from libvirtpy.rpc.typed_params import from_wire, to_wire


def typed(name: str, code: int, value: float | int | str) -> types.TypedParam:
    """Build a wire parameter."""
    return types.TypedParam(
        field=name, value=types.TypedParamValue(type=code, value=value)
    )


def test_documented_names_get_the_documented_width() -> None:
    wire = to_wire({"hard_limit": 4096, "weight": 500, "vcpu_quota": -1})

    assert [(p.field, p.value.type) for p in wire] == [
        ("hard_limit", 4),  # ullong
        ("weight", 2),  # uint
        ("vcpu_quota", 3),  # llong
    ]


@pytest.mark.parametrize(
    ("value", "code"),
    [(True, 6), (1.5, 5), ("text", 7), (7, 4), (-7, 3)],
)
def test_unknown_names_are_typed_from_the_python_value(
    value: object, code: int
) -> None:
    (parameter,) = to_wire({"some-new-parameter": value})  # type: ignore[dict-item]

    assert parameter.value.type == code


@pytest.mark.parametrize(
    ("name", "value"),
    [("hard_limit", "lots"), ("weight", 1.5), ("group_name", 3)],
)
def test_a_value_that_does_not_fit_its_type_is_refused(
    name: str, value: object
) -> None:
    with pytest.raises(TypeError, match=name):
        to_wire({name: value})  # type: ignore[dict-item]


def test_wire_parameters_become_a_dict_with_real_booleans() -> None:
    values = from_wire(
        [typed("cmt", 6, 1), typed("cpu_shares", 4, 2048), typed("g", 7, "x")]
    )

    assert values == {"cmt": True, "cpu_shares": 2048, "g": "x"}
