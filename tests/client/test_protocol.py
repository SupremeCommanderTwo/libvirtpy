"""The generated wire protocol: every struct round-trips, procedures are sane."""

import inspect
from dataclasses import fields, is_dataclass
from enum import IntEnum
from typing import Any

import pytest

from libvirtpy.rpc.protocol import procedures, types
from libvirtpy.rpc.xdr import (
    Array,
    EnumType,
    FixedArray,
    FixedOpaque,
    OptionalOf,
    String,
    StructType,
    UnionType,
    VarOpaque,
    XdrType,
    decode,
    encode,
)

STRUCTS = [
    cls
    for _, cls in inspect.getmembers(types, inspect.isclass)
    if is_dataclass(cls) and hasattr(cls, "xdr_fields")
]
UNIONS = [
    cls
    for _, cls in inspect.getmembers(types, inspect.isclass)
    if is_dataclass(cls) and hasattr(cls, "xdr_arms")
]


def sample(xdr_type: XdrType, depth: int = 0) -> Any:
    """Build a small value of a descriptor's type."""
    if isinstance(xdr_type, String):
        return "ab"
    if isinstance(xdr_type, VarOpaque):
        return b"abc"
    if isinstance(xdr_type, FixedOpaque):
        return bytes(range(xdr_type.size))
    if isinstance(xdr_type, Array):
        return [sample(xdr_type.item, depth + 1)] if depth < 3 else []
    if isinstance(xdr_type, FixedArray):
        return [sample(xdr_type.item, depth + 1) for _ in range(xdr_type.size)]
    if isinstance(xdr_type, OptionalOf):
        return None if depth else sample(xdr_type.item, depth + 1)
    if isinstance(xdr_type, EnumType):
        return next(iter(xdr_type.enum))
    if isinstance(xdr_type, StructType):
        return build(xdr_type.cls, depth + 1)
    if isinstance(xdr_type, UnionType):
        return build_union(xdr_type.cls, depth + 1)
    return sample_number(xdr_type)


def sample_number(xdr_type: XdrType) -> Any:
    """Build a number, boolean or float for a scalar descriptor."""
    fmt = getattr(xdr_type, "fmt", None)
    if fmt in (">f", ">d"):
        return 0.5
    return 1 if fmt else True


def build(cls: Any, depth: int = 0) -> Any:
    """Build an instance of a generated struct."""
    return cls(**{name: sample(t, depth) for name, t in cls.xdr_fields})


def build_union(cls: Any, depth: int = 0) -> Any:
    """Build an instance of a generated union, using its first arm."""
    name, _ = cls.xdr_discriminant
    label, arm = next(iter(cls.xdr_arms.items()))
    value = None if arm is None else sample(arm, depth)
    return cls(**{name: label, "value": value})


def test_the_protocol_has_the_expected_size() -> None:
    assert len(procedures.PROCEDURES) == 456
    assert len(STRUCTS) >= 700


@pytest.mark.parametrize("cls", STRUCTS, ids=lambda cls: cls.__name__)
def test_struct_round_trips(cls: Any) -> None:
    value = build(cls)

    assert decode(StructType(cls), encode(StructType(cls), value)) == value


@pytest.mark.parametrize("cls", UNIONS, ids=lambda cls: cls.__name__)
def test_union_round_trips(cls: Any) -> None:
    value = build_union(cls)

    assert decode(UnionType(cls), encode(UnionType(cls), value)) == value


def test_every_struct_field_is_declared_in_the_layout() -> None:
    for cls in STRUCTS:
        declared = [name for name, _ in cls.xdr_fields]
        assert declared == [field.name for field in fields(cls)], cls.__name__


def test_message_header_is_24_bytes_with_the_documented_layout() -> None:
    header = types.VirNetMessageHeader(
        prog=types.REMOTE_PROGRAM,
        vers=types.REMOTE_PROTOCOL_VERSION,
        proc=procedures.CONNECT_OPEN.number,
        type=types.VirNetMessageType.CALL,
        serial=1,
        status=types.VirNetMessageStatus.OK,
    )

    data = encode(StructType(types.VirNetMessageHeader), header)

    assert data.hex() == "200080860000000100000001000000000000000100000000"


def test_procedure_numbers_and_names_are_unique() -> None:
    every = list(procedures.PROCEDURES.values())

    assert len({p.number for p in every}) == len(every)
    assert len({p.name for p in every}) == len(every)


@pytest.mark.parametrize(
    ("procedure", "driver"),
    [
        (procedures.CONNECT_OPEN, "hypervisor"),
        (procedures.DOMAIN_LOOKUP_BY_NAME, "hypervisor"),
        (procedures.DOMAIN_SNAPSHOT_LOOKUP_BY_NAME, "hypervisor"),
        (procedures.NETWORK_LOOKUP_BY_NAME, "network"),
        (procedures.CONNECT_LIST_ALL_NETWORKS, "network"),
        (procedures.STORAGE_VOL_GET_XML_DESC, "storage"),
        (procedures.CONNECT_LIST_ALL_STORAGE_POOLS, "storage"),
        (procedures.SECRET_GET_VALUE, "secret"),
        (procedures.NWFILTER_BINDING_LOOKUP_BY_PORT_DEV, "nwfilter"),
        (procedures.NODE_DEVICE_GET_XML_DESC, "node_device"),
        (procedures.NODE_DEVICE_DETACH_FLAGS, "hypervisor"),
        (procedures.INTERFACE_LOOKUP_BY_NAME, "interface"),
    ],
)
def test_procedure_is_routed_to_the_right_daemon(procedure: Any, driver: str) -> None:
    assert procedure.driver == driver


def test_keepalive_and_error_types_exist() -> None:
    assert issubclass(types.KeepaliveProcedure, IntEnum)
    assert int(types.KeepaliveProcedure.PING) == 1
    assert hasattr(types, "Error")
