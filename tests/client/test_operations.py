"""Operations are sans-I/O: drive them with scripted replies."""

import pytest

from libvirtpy.client import operations
from libvirtpy.client.transport import Handle, Request
from libvirtpy.rpc.errors import NoDomainError

DOMAIN_XML = "<domain type='kvm'><name>vm</name></domain>"


def test_lookup_domain_by_name_asks_for_the_name_then_the_xml() -> None:
    operation = operations.lookup_domain("vm")

    first = next(operation)
    second = operation.send(Handle(name="vm"))
    with pytest.raises(StopIteration) as finished:
        operation.send(DOMAIN_XML)

    assert first == Request("domain_lookup_by_name", {"name": "vm"})
    assert second.procedure == "domain_get_xml_desc"
    assert finished.value.value.name == "vm"


def test_lookup_domain_by_integer_uses_the_runtime_id() -> None:
    request = next(operations.lookup_domain(7))

    assert request == Request("domain_lookup_by_id", {"id": 7})


def test_lookup_domain_by_uuid_text_uses_the_uuid() -> None:
    uuid_text = "3f0c5a52-2c27-4c26-a1f6-8c2b0d3a9a11"

    request = next(operations.lookup_domain(uuid_text))

    assert request == Request("domain_lookup_by_uuid", {"uuid": uuid_text})


def test_a_daemon_error_is_raised_inside_the_operation() -> None:
    operation = operations.lookup_domain("vm")
    next(operation)

    with pytest.raises(NoDomainError):
        operation.throw(NoDomainError("gone", code=42))
