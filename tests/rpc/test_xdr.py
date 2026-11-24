"""The XDR codec against the byte layouts of RFC 4506."""

from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar

import pytest

from libvirtpy.rpc.xdr import (
    BOOL,
    DOUBLE,
    HYPER,
    INT,
    UHYPER,
    UINT,
    Array,
    EnumType,
    FixedArray,
    FixedOpaque,
    OptionalOf,
    String,
    StructType,
    UnionType,
    VarOpaque,
    XdrError,
    XdrType,
    decode,
    encode,
)


class Color(IntEnum):
    RED = 1
    BLUE = 2


@dataclass
class Point:
    x: int
    label: str

    xdr_fields: ClassVar[tuple[tuple[str, XdrType], ...]] = (
        ("x", INT),
        ("label", String(8)),
    )


@dataclass
class Choice:
    kind: int
    value: int | str | None

    xdr_discriminant: ClassVar[tuple[str, XdrType]] = ("kind", INT)
    xdr_arms: ClassVar[dict[int, XdrType | None]] = {1: INT, 2: String(), 3: None}


@pytest.mark.parametrize(
    ("xdr_type", "value", "expected"),
    [
        (INT, -1, "ffffffff"),
        (INT, 5, "00000005"),
        (UINT, 4294967295, "ffffffff"),
        (HYPER, -2, "fffffffffffffffe"),
        (UHYPER, 1, "0000000000000001"),
        (BOOL, True, "00000001"),
        (BOOL, False, "00000000"),
        (DOUBLE, 1.5, "3ff8000000000000"),
        (String(), "abc", "0000000361626300"),
        (String(), "", "00000000"),
        (FixedOpaque(5), b"hello", "68656c6c6f000000"),
        (VarOpaque(), b"\x01\x02", "0000000201020000"),
        (Array(INT), [1, 2], "000000020000000100000002"),
        (FixedArray(INT, 2), [7, 8], "0000000700000008"),
        (OptionalOf(INT), None, "00000000"),
        (OptionalOf(INT), 9, "0000000100000009"),
        (EnumType(Color), Color.BLUE, "00000002"),
    ],
)
def test_encoding_matches_the_rfc_layout(
    xdr_type: XdrType, value: object, expected: str
) -> None:
    data = encode(xdr_type, value)

    assert data.hex() == expected
    assert decode(xdr_type, data) == value


def test_struct_is_written_field_after_field() -> None:
    struct_type = StructType(Point)

    data = encode(struct_type, Point(x=3, label="hi"))

    assert data.hex() == "000000030000000268690000"
    assert decode(struct_type, data) == Point(x=3, label="hi")


@pytest.mark.parametrize("choice", [Choice(1, 42), Choice(2, "text"), Choice(3, None)])
def test_union_round_trips_each_arm(choice: Choice) -> None:
    union_type = UnionType(Choice)

    assert decode(union_type, encode(union_type, choice)) == choice


@pytest.mark.parametrize(
    ("xdr_type", "data"),
    [
        (INT, b"\x00\x00"),
        (String(), b"\x00\x00\x00\x05abc"),
        (String(2), b"\x00\x00\x00\x03abc\x00"),
        (String(), b"\x00\x00\x00\x01\xff\x00\x00\x00"),
        (String(), b"\x00\x00\x00\x01a\x00\x00\x01"),
        (BOOL, b"\x00\x00\x00\x02"),
        (OptionalOf(INT), b"\x00\x00\x00\x02"),
        (Array(INT, 1), b"\x00\x00\x00\x02" + bytes(8)),
        (Array(INT), b"\xff\xff\xff\xff"),
        (EnumType(Color), b"\x00\x00\x00\x09"),
        (UnionType(Choice), b"\x00\x00\x00\x09"),
        (INT, b"\x00\x00\x00\x01\x00"),
    ],
)
def test_malformed_data_is_an_xdr_error(xdr_type: XdrType, data: bytes) -> None:
    with pytest.raises(XdrError):
        decode(xdr_type, data)


@pytest.mark.parametrize(
    ("xdr_type", "value"),
    [
        (INT, 2**31),
        (UINT, -1),
        (String(2), "abc"),
        (FixedOpaque(2), b"abc"),
        (VarOpaque(1), b"ab"),
        (Array(INT, 1), [1, 2]),
        (FixedArray(INT, 2), [1]),
    ],
)
def test_values_that_do_not_fit_are_an_xdr_error(
    xdr_type: XdrType, value: object
) -> None:
    with pytest.raises(XdrError):
        encode(xdr_type, value)
