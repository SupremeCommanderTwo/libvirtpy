"""libvirt's typed parameters: ``dict`` in Python, a list of typed values on the wire.

Setters such as ``set_domain_memory_parameters`` take a dict. The daemon needs
the exact integer width of each named parameter, which libvirt's headers
document; ``protocol/typed_hints.py`` has them. A name that is not in the table
is typed from its Python value: ``bool`` boolean, ``float`` double, ``str`` text,
non-negative ``int`` ullong, negative ``int`` llong.
"""

from collections.abc import Mapping

from libvirtpy.rpc.protocol import types
from libvirtpy.rpc.protocol.typed_hints import TYPED_PARAMETER_HINTS

__all__ = ["TypedValue", "from_wire", "to_wire"]

TypedValue = int | float | bool | str

_INT, _UINT, _LLONG, _ULLONG, _DOUBLE, _BOOLEAN, _STRING = range(1, 8)
_INTEGER_TYPES = {_INT, _UINT, _LLONG, _ULLONG}


def to_wire(parameters: Mapping[str, TypedValue]) -> list[types.TypedParam]:
    """Turn a dict into the wire list of typed parameters.

    :param parameters: parameter name -> value.
    :returns: the typed parameters, in the dict's order.
    :raises TypeError: if a value does not fit the documented type of its name.
    """
    return [
        types.TypedParam(
            field=name,
            value=types.TypedParamValue(type=code, value=_convert(name, code, value)),
        )
        for name, value in parameters.items()
        for code in [_type_of(name, value)]
    ]


def from_wire(parameters: list[types.TypedParam]) -> dict[str, TypedValue]:
    """Turn the wire list of typed parameters into a dict.

    A boolean (wire type 6) becomes ``bool``; the other values keep their Python
    type (``int``, ``float``, ``str``).

    :param parameters: the typed parameters of a reply.
    :returns: parameter name -> value.
    """
    values: dict[str, TypedValue] = {}
    for parameter in parameters:
        value = parameter.value.value
        if parameter.value.type == _BOOLEAN:
            value = bool(value)
        values[parameter.field] = value  # type: ignore[assignment]  # the union holds only TypedValue types
    return values


def _type_of(name: str, value: TypedValue) -> int:
    """Choose the wire type of a parameter.

    :param name: the parameter name.
    :param value: the Python value.
    :returns: the wire type code: the documented one, else inferred.
    """
    if name in TYPED_PARAMETER_HINTS:
        return TYPED_PARAMETER_HINTS[name]
    if isinstance(value, bool):
        return _BOOLEAN
    if isinstance(value, float):
        return _DOUBLE
    if isinstance(value, str):
        return _STRING
    return _ULLONG if value >= 0 else _LLONG


def _convert(name: str, code: int, value: TypedValue) -> int | float | str:
    """Check a value against its wire type.

    :param name: the parameter name, for the error message.
    :param code: the wire type code.
    :param value: the Python value.
    :returns: the value for the wire.
    :raises TypeError: if the value cannot be of that type.
    """
    if code == _STRING and isinstance(value, str):
        return value
    if code == _DOUBLE and isinstance(value, int | float):
        return float(value)
    if code == _BOOLEAN and isinstance(value, bool | int):
        return int(bool(value))
    if (
        code in _INTEGER_TYPES
        and isinstance(value, int)
        and not isinstance(value, bool)
    ):
        return value
    raise TypeError(f"parameter {name!r}: {value!r} does not fit wire type {code}")
