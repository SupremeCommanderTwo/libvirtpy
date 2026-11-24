"""Both clients against the in-memory daemon give the same results."""

import asyncio

import pytest

from libvirtpy.client import (
    AsyncFakeTransport,
    AsyncLibvirtClient,
    DomainState,
    FakeLibvirt,
    LibvirtClient,
)
from libvirtpy.rpc.errors import NoDomainError, OperationInvalidError
from libvirtpy.xml import Domain


def _domain(name: str) -> Domain:
    return Domain.from_xml(f"<domain type='kvm'><name>{name}</name></domain>")


def test_define_fills_in_the_uuid() -> None:
    client = LibvirtClient(FakeLibvirt())

    domain = client.define_domain(_domain("vm"))

    assert domain.uuid is not None


def test_start_then_shutdown_changes_the_state() -> None:
    client = LibvirtClient(FakeLibvirt())
    client.define_domain(_domain("vm"))

    client.start_domain("vm")
    running = client.get_domain_state("vm")
    client.shutdown_domain("vm")

    assert running == DomainState.RUNNING
    assert client.get_domain_state("vm") == DomainState.SHUTOFF


def test_proxy_and_flat_style_agree() -> None:
    client = LibvirtClient(FakeLibvirt())
    client.define_domain(_domain("vm"))

    client.domain("vm").set_vcpus(3)

    vcpu = client.lookup_domain("vm").vcpu
    assert vcpu is not None
    assert vcpu.value == 3


def test_missing_domain_raises_the_specific_error() -> None:
    client = LibvirtClient(FakeLibvirt())

    with pytest.raises(NoDomainError):
        client.lookup_domain("nope")


def test_starting_twice_raises_operation_invalid() -> None:
    client = LibvirtClient(FakeLibvirt())
    client.define_domain(_domain("vm"))
    client.start_domain("vm")

    with pytest.raises(OperationInvalidError):
        client.start_domain("vm")


def test_async_client_matches_the_sync_client() -> None:
    async def scenario() -> tuple[str, DomainState]:
        async with AsyncLibvirtClient(AsyncFakeTransport()) as client:
            await client.define_domain(_domain("vm"))
            await client.start_domain("vm")
            found = await client.lookup_domain("vm")
            return found.name, await client.get_domain_state("vm")

    name, state = asyncio.run(scenario())

    assert name == "vm"
    assert state == DomainState.RUNNING
