"""XDR (RFC 4506) encoding and decoding, driven by type descriptors.

The generated protocol module describes every wire structure as a dataclass with
a ``xdr_fields`` table of ``(attribute name, XdrType)``; the descriptors here
turn such a value into bytes and back. Everything is big-endian and padded to
four bytes, as the standard says.
"""

import struct
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, ClassVar, Protocol, TypeVar

from libvirtpy.errors import LibvirtPyError

__all__ = [
    "BOOL",
    "DOUBLE",
    "FLOAT",
    "HYPER",
    "INT",
    "UHYPER",
    "UINT",
    "Array",
    "Decoder",
    "Encoder",
    "EnumType",
    "FixedArray",
    "FixedOpaque",
    "OptionalOf",
    "String",
    "StructType",
    "UnionType",
    "VarOpaque",
    "XdrError",
    "XdrType",
    "decode",
    "encode",
]

UNBOUNDED = 2**32 - 1
"""The XDR limit of a variable-length item that declares no bound."""

T = TypeVar("T")


class XdrError(LibvirtPyError):
    """Data does not follow the XDR layout it should."""


class Encoder:
    """Collects the bytes of an XDR value."""

    def __init__(self) -> None:
        """Create an empty encoder."""
        self._buffer = bytearray()

    def getvalue(self) -> bytes:
        """Return everything written so far.

        :returns: the encoded bytes.
        """
        return bytes(self._buffer)

    def pack(self, fmt: str, value: int | float) -> None:
        """Write a number with a ``struct`` format.

        :param fmt: a big-endian ``struct`` format, e.g. ``">i"``.
        :param value: the number.
        :raises XdrError: if the number does not fit the format.
        """
        try:
            self._buffer += struct.pack(fmt, value)
        except struct.error as error:
            raise XdrError(f"cannot encode {value!r} as {fmt!r}: {error}") from error

    def write_opaque(self, data: bytes) -> None:
        """Write bytes followed by the padding to a multiple of four.

        :param data: the bytes.
        """
        self._buffer += data
        self._buffer += b"\0" * (-len(data) % 4)


class Decoder:
    """Reads XDR values from bytes."""

    def __init__(self, data: bytes) -> None:
        """Create a decoder at the start of ``data``.

        :param data: the bytes to read.
        """
        self._data = data
        self._offset = 0

    @property
    def remaining(self) -> int:
        """The number of bytes not read yet."""
        return len(self._data) - self._offset

    def unpack(self, fmt: str) -> Any:  # struct.unpack returns Any-typed items
        """Read one number with a ``struct`` format.

        :param fmt: a big-endian ``struct`` format of one item, e.g. ``">i"``.
        :returns: the number.
        :raises XdrError: if there are not enough bytes.
        """
        (value,) = struct.unpack(fmt, self.read(struct.calcsize(fmt)))
        return value

    def read(self, count: int) -> bytes:
        """Read raw bytes.

        :param count: how many bytes.
        :returns: the bytes.
        :raises XdrError: if fewer than ``count`` bytes remain.
        """
        if count > self.remaining:
            raise XdrError(f"need {count} bytes, {self.remaining} left")

        start = self._offset
        self._offset += count
        return self._data[start : self._offset]

    def read_opaque(self, count: int) -> bytes:
        """Read ``count`` bytes and skip their padding.

        :param count: the length of the data.
        :returns: the data without the padding.
        :raises XdrError: if the data or the padding is missing or not zero.
        """
        data = self.read(count)
        padding = self.read(-count % 4)
        if padding.strip(b"\0"):
            raise XdrError("padding is not zero")
        return data


class XdrType(Protocol):
    """How to write and read one kind of value."""

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write ``value``.

        :param encoder: where to write.
        :param value: the value to write.
        """

    def decode(self, decoder: Decoder) -> Any:
        """Read a value.

        :param decoder: where to read.
        :returns: the value.
        """


@dataclass(frozen=True)
class _Number:
    """A number with a fixed ``struct`` format."""

    fmt: str
    convert: Callable[[Any], Any] = lambda value: value

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the number.

        :param encoder: where to write.
        :param value: the number.
        """
        encoder.pack(self.fmt, self.convert(value))

    def decode(self, decoder: Decoder) -> Any:
        """Read the number.

        :param decoder: where to read.
        :returns: the number.
        """
        return decoder.unpack(self.fmt)


@dataclass(frozen=True)
class _Boolean:
    """An XDR ``bool``: the integer 0 or 1."""

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the boolean.

        :param encoder: where to write.
        :param value: the boolean.
        """
        encoder.pack(">I", 1 if value else 0)

    def decode(self, decoder: Decoder) -> bool:
        """Read the boolean.

        :param decoder: where to read.
        :returns: the boolean.
        :raises XdrError: if the integer is neither 0 nor 1.
        """
        number = decoder.unpack(">I")
        if number > 1:
            raise XdrError(f"{number} is not a boolean")
        return bool(number == 1)


INT = _Number(">i")
UINT = _Number(">I")
HYPER = _Number(">q")
UHYPER = _Number(">Q")
FLOAT = _Number(">f")
DOUBLE = _Number(">d")
BOOL = _Boolean()


@dataclass(frozen=True)
class String:
    """A UTF-8 string of at most ``maximum`` bytes."""

    maximum: int = UNBOUNDED

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the string.

        :param encoder: where to write.
        :param value: the text.
        :raises XdrError: if it is longer than the maximum.
        """
        data = value.encode("utf-8")
        if len(data) > self.maximum:
            raise XdrError(f"string of {len(data)} bytes, maximum {self.maximum}")
        encoder.pack(">I", len(data))
        encoder.write_opaque(data)

    def decode(self, decoder: Decoder) -> str:
        """Read the string.

        :param decoder: where to read.
        :returns: the text.
        :raises XdrError: if it is too long or not valid UTF-8.
        """
        length = decoder.unpack(">I")
        if length > self.maximum:
            raise XdrError(f"string of {length} bytes, maximum {self.maximum}")
        data = decoder.read_opaque(length)
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise XdrError(f"string is not UTF-8: {error}") from error


@dataclass(frozen=True)
class FixedOpaque:
    """Exactly ``size`` bytes."""

    size: int

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the bytes.

        :param encoder: where to write.
        :param value: the bytes.
        :raises XdrError: if the length is not ``size``.
        """
        if len(value) != self.size:
            raise XdrError(f"need {self.size} bytes, got {len(value)}")
        encoder.write_opaque(bytes(value))

    def decode(self, decoder: Decoder) -> bytes:
        """Read the bytes.

        :param decoder: where to read.
        :returns: the bytes.
        """
        return decoder.read_opaque(self.size)


@dataclass(frozen=True)
class VarOpaque:
    """At most ``maximum`` bytes, with a length in front."""

    maximum: int = UNBOUNDED

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the bytes.

        :param encoder: where to write.
        :param value: the bytes.
        :raises XdrError: if there are more than the maximum.
        """
        if len(value) > self.maximum:
            raise XdrError(f"{len(value)} bytes, maximum {self.maximum}")
        encoder.pack(">I", len(value))
        encoder.write_opaque(bytes(value))

    def decode(self, decoder: Decoder) -> bytes:
        """Read the bytes.

        :param decoder: where to read.
        :returns: the bytes.
        :raises XdrError: if there are more than the maximum.
        """
        length = decoder.unpack(">I")
        if length > self.maximum:
            raise XdrError(f"{length} bytes, maximum {self.maximum}")
        return decoder.read_opaque(length)


@dataclass(frozen=True)
class Array:
    """At most ``maximum`` items, with a count in front."""

    item: XdrType
    maximum: int = UNBOUNDED

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the items.

        :param encoder: where to write.
        :param value: the items.
        :raises XdrError: if there are more than the maximum.
        """
        if len(value) > self.maximum:
            raise XdrError(f"{len(value)} items, maximum {self.maximum}")
        encoder.pack(">I", len(value))
        for item in value:
            self.item.encode(encoder, item)

    def decode(self, decoder: Decoder) -> list[Any]:
        """Read the items.

        :param decoder: where to read.
        :returns: the items.
        :raises XdrError: if there are more than the maximum or more than the
            remaining bytes could hold.
        """
        count = decoder.unpack(">I")
        if count > self.maximum or count > decoder.remaining:
            raise XdrError(f"{count} items, maximum {self.maximum}")
        return [self.item.decode(decoder) for _ in range(count)]


@dataclass(frozen=True)
class FixedArray:
    """Exactly ``size`` items, without a count."""

    item: XdrType
    size: int

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the items.

        :param encoder: where to write.
        :param value: the items.
        :raises XdrError: if the count is not ``size``.
        """
        if len(value) != self.size:
            raise XdrError(f"need {self.size} items, got {len(value)}")
        for item in value:
            self.item.encode(encoder, item)

    def decode(self, decoder: Decoder) -> list[Any]:
        """Read the items.

        :param decoder: where to read.
        :returns: the items.
        """
        return [self.item.decode(decoder) for _ in range(self.size)]


@dataclass(frozen=True)
class OptionalOf:
    """A value that may be absent (``T *name`` in XDR)."""

    item: XdrType

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the flag and, if present, the value.

        :param encoder: where to write.
        :param value: the value, or ``None``.
        """
        encoder.pack(">I", 0 if value is None else 1)
        if value is not None:
            self.item.encode(encoder, value)

    def decode(self, decoder: Decoder) -> Any:
        """Read the flag and, if present, the value.

        :param decoder: where to read.
        :returns: the value, or ``None``.
        :raises XdrError: if the flag is neither 0 nor 1.
        """
        flag = decoder.unpack(">I")
        if flag > 1:
            raise XdrError(f"{flag} is not an optional flag")
        return self.item.decode(decoder) if flag else None


@dataclass(frozen=True)
class EnumType:
    """A member of an ``IntEnum``, written as a signed integer."""

    enum: type[IntEnum]

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the member.

        :param encoder: where to write.
        :param value: a member or its number.
        """
        encoder.pack(">i", int(value))

    def decode(self, decoder: Decoder) -> IntEnum:
        """Read the member.

        :param decoder: where to read.
        :returns: the member.
        :raises XdrError: if the number is not a member.
        """
        number = decoder.unpack(">i")
        try:
            return self.enum(number)
        except ValueError as error:
            raise XdrError(f"{number} is not a {self.enum.__name__}") from error


class XdrStruct(Protocol):
    """A dataclass with an ``xdr_fields`` table."""

    xdr_fields: ClassVar[tuple[tuple[str, XdrType], ...]]

    def __init__(self, **fields: Any) -> None:
        """Create the struct from its fields.

        :param fields: the fields by attribute name.
        """


@dataclass(frozen=True)
class StructType:
    """A generated dataclass, written field after field."""

    cls: type[XdrStruct]

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the fields.

        :param encoder: where to write.
        :param value: an instance of the class.
        """
        for name, xdr_type in self.cls.xdr_fields:
            xdr_type.encode(encoder, getattr(value, name))

    def decode(self, decoder: Decoder) -> Any:
        """Read the fields.

        :param decoder: where to read.
        :returns: an instance of the class.
        """
        fields = {
            name: xdr_type.decode(decoder) for name, xdr_type in self.cls.xdr_fields
        }
        return self.cls(**fields)


class XdrUnion(Protocol):
    """A dataclass with a discriminant, a value and the arms table."""

    xdr_discriminant: ClassVar[tuple[str, XdrType]]
    xdr_arms: ClassVar[dict[int, XdrType | None]]

    def __init__(self, **fields: Any) -> None:
        """Create the union from its fields.

        :param fields: the discriminant and the value.
        """


@dataclass(frozen=True)
class UnionType:
    """A generated dataclass with a discriminant and the value of one arm."""

    cls: type[XdrUnion]

    def encode(self, encoder: Encoder, value: Any) -> None:
        """Write the discriminant and the value of its arm.

        :param encoder: where to write.
        :param value: an instance of the class.
        :raises XdrError: if the discriminant has no arm.
        """
        name, discriminant_type = self.cls.xdr_discriminant
        discriminant = int(getattr(value, name))
        arm = self._arm(discriminant)

        discriminant_type.encode(encoder, discriminant)
        if arm is not None:
            arm.encode(encoder, value.value)

    def decode(self, decoder: Decoder) -> Any:
        """Read the discriminant and the value of its arm.

        :param decoder: where to read.
        :returns: an instance of the class.
        :raises XdrError: if the discriminant has no arm.
        """
        name, discriminant_type = self.cls.xdr_discriminant
        discriminant = int(discriminant_type.decode(decoder))
        arm = self._arm(discriminant)

        item = None if arm is None else arm.decode(decoder)
        return self.cls(**{name: discriminant, "value": item})

    def _arm(self, discriminant: int) -> XdrType | None:
        """Find the type of the arm of a discriminant.

        :param discriminant: the value of the discriminant.
        :returns: the arm's type, or ``None`` for a void arm.
        :raises XdrError: if there is no such arm.
        """
        if discriminant not in self.cls.xdr_arms:
            raise XdrError(f"no union arm for {discriminant}")
        return self.cls.xdr_arms[discriminant]


def encode(xdr_type: XdrType, value: Any) -> bytes:
    """Encode one value.

    :param xdr_type: its type.
    :param value: the value.
    :returns: the encoded bytes.
    """
    encoder = Encoder()
    xdr_type.encode(encoder, value)
    return encoder.getvalue()


def decode(xdr_type: XdrType, data: bytes) -> Any:
    """Decode one value that takes all of ``data``.

    :param xdr_type: its type.
    :param data: the bytes.
    :returns: the value.
    :raises XdrError: if the data is malformed or has bytes left over.
    """
    decoder = Decoder(data)
    value = xdr_type.decode(decoder)
    if decoder.remaining:
        raise XdrError(f"{decoder.remaining} bytes left after the value")
    return value
