"""Shared annotated types used across all models."""

import re
from collections.abc import Callable
from typing import Annotated

from pydantic import BeforeValidator, Field, PlainSerializer, StringConstraints
from pydantic_xml import attr

from libvirtpy.xml._base import LibvirtXmlModel

__all__ = [
    "HexNumber",
    "OnOff",
    "OptionalText",
    "PresenceFlag",
    "ScaledInteger",
    "SizeUnit",
    "Uuid",
    "YesNo",
    "size_to_bytes",
]


def _bool_parser(true_word: str, false_word: str) -> Callable[[object], bool]:
    """Build a validator that accepts only ``true_word``, ``false_word`` or ``bool``.

    The check is done here, not with pydantic's ``Strict()``: pydantic-xml
    validates with ``strict=False``, which would let pydantic's lax ``bool``
    accept ``"true"``, ``"1"`` and the other word pair (``"on"`` for yes/no).

    :param true_word: the text that means ``True``, e.g. ``"yes"``.
    :param false_word: the text that means ``False``, e.g. ``"no"``.
    :returns: the validator function.
    """
    words = {true_word: True, false_word: False}

    def parse(value: object) -> bool:
        """Convert one value to ``bool``.

        :param value: a ``bool`` or one of the two accepted words.
        :returns: the ``bool`` value.
        :raises ValueError: if ``value`` is anything else.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value in words:
            return words[value]
        raise ValueError(f"expected {true_word!r} or {false_word!r}, got {value!r}")

    return parse


def _bool_serializer(true_word: str, false_word: str) -> Callable[[bool], str]:
    """Build a serializer that writes ``True`` and ``False`` as words.

    :param true_word: the text written for ``True``.
    :param false_word: the text written for ``False``.
    :returns: the serializer function.
    """

    def serialize(value: bool) -> str:
        """Write one ``bool`` as its word.

        :param value: the value to write.
        :returns: the word for ``value``.
        """
        return true_word if value else false_word

    return serialize


YesNo = Annotated[
    bool,
    BeforeValidator(_bool_parser("yes", "no")),
    PlainSerializer(_bool_serializer("yes", "no"), return_type=str),
]
"""A ``yes``/``no`` attribute value as ``bool``."""

OnOff = Annotated[
    bool,
    BeforeValidator(_bool_parser("on", "off")),
    PlainSerializer(_bool_serializer("on", "off"), return_type=str),
]
"""An ``on``/``off`` attribute value as ``bool``."""


def _empty_to_none(value: object) -> object:
    """Turn an empty string into ``None``, leave other values alone.

    :param value: the raw value of an element's text.
    :returns: ``None`` for ``""``, otherwise ``value`` unchanged.
    """
    if value == "":
        return None
    return value


OptionalText = Annotated[str | None, BeforeValidator(_empty_to_none)]
"""Element text that may be missing, for a model that also has attributes.

``<loader readonly='yes'/>`` has no path: it parses to ``None``, not ``""``.
Use it as ``value: OptionalText = None``.
"""


class PresenceFlag(LibvirtXmlModel):
    """An empty element whose presence is the information, like ``<acpi/>``.

    Use it as ``PresenceFlag | None``: ``None`` means the element is absent.
    The element tag comes from the field, e.g. ``element(tag="acpi")``.
    A ``bool`` field cannot be used: pydantic-xml reads an empty element as
    missing and cannot write an empty element for ``True``.
    """


HexNumber = Annotated[str, StringConstraints(pattern=r"^(0x)?[0-9a-fA-F]+$")]
"""A number written in hex (``0x1f``) or decimal (``31``), kept as written.

Used for device addresses, where libvirt accepts both forms.
"""

Uuid = Annotated[
    str,
    StringConstraints(
        pattern=r"^([a-fA-F0-9]{32}|[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})$"
    ),
]
"""A UUID kept exactly as written (with or without dashes, any case)."""


# Same as the "unit" define of libvirt's basictypes.rng.
_SIZE_UNIT_PATTERN = r"^([bB]([yY][tT][eE][sS]?)?|[kKmMgGtTpPeE]([iI]?[bB])?)$"

SizeUnit = Annotated[str, StringConstraints(pattern=_SIZE_UNIT_PATTERN)]
"""A size unit as accepted by libvirt: ``b``, ``byte(s)``, ``KB``, ``KiB``, ``k``...

Kept as written (``"GiB"`` stays ``"GiB"``); the libvirt schema accepts these
case-insensitively, so a ``Literal`` would reject valid documents.
"""

_DECIMAL_FACTORS = {
    "k": 1000**1,
    "m": 1000**2,
    "g": 1000**3,
    "t": 1000**4,
    "p": 1000**5,
    "e": 1000**6,
}
_BINARY_FACTORS = {
    "k": 1024**1,
    "m": 1024**2,
    "g": 1024**3,
    "t": 1024**4,
    "p": 1024**5,
    "e": 1024**6,
}


def size_to_bytes(value: int, unit: SizeUnit) -> int:
    """Convert ``value`` in ``unit`` to bytes, following libvirt's rules.

    ``KB``, ``MB``... are powers of 1000; ``k``, ``KiB``, ``M``, ``MiB``... are
    powers of 1024.

    :param value: the amount.
    :param unit: the libvirt unit of ``value``, such as ``"GiB"`` or ``"KB"``.
    :returns: the amount in bytes.
    :raises ValueError: if ``unit`` is not a libvirt size unit.
    """
    if re.fullmatch(_SIZE_UNIT_PATTERN, unit) is None:
        raise ValueError(f"unknown size unit: {unit!r}")

    normalized = unit.lower()
    if normalized in ("b", "byte", "bytes"):
        return value

    prefix = normalized[0]
    is_decimal = len(normalized) == 2 and normalized.endswith("b")  # "kb", "mb"...
    if is_decimal:
        return value * _DECIMAL_FACTORS[prefix]
    return value * _BINARY_FACTORS[prefix]


class ScaledInteger(LibvirtXmlModel):
    """Base of elements that hold an amount with an optional ``unit``.

    Subclass it with a ``tag``, e.g. ``class Limit(ScaledInteger, tag="limit")``.
    The unit is kept as written; ``to_bytes()`` converts explicitly.
    """

    value: int = Field(ge=0, description="Element text: the amount, in ``unit``.")
    unit: SizeUnit | None = attr(name="unit", default=None)

    def to_bytes(self) -> int:
        """Return the amount in bytes (a missing ``unit`` means KiB)."""
        return size_to_bytes(self.value, self.unit or "KiB")
