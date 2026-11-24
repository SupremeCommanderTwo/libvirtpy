"""Read-only checks against the libvirt daemon of this machine (``pytest -m libvirt``).

Nothing here changes the host: it lists and reads. The tests skip when no
daemon socket can be reached or the user may not connect.
"""

from collections.abc import Iterator

import pytest

from libvirtpy.client import LibvirtClient
from libvirtpy.rpc.errors import NoDomainError

pytestmark = pytest.mark.libvirt


@pytest.fixture(scope="module")
def client() -> Iterator[LibvirtClient]:
    """A connection to ``qemu:///system``, or skip the module."""
    try:
        connection = LibvirtClient.open("qemu:///system")
    except (ConnectionError, OSError) as error:
        pytest.skip(f"no libvirt daemon to talk to: {error}")
    with connection:
        yield connection


def test_version_and_host_capabilities(client: LibvirtClient) -> None:
    assert client.get_version() > 0
    assert client.get_capabilities().guests


def test_domains_are_parsed_into_models(client: LibvirtClient) -> None:
    domains = client.list_domains()

    for domain in domains:
        found = client.lookup_domain(domain)
        assert found.name == domain.name
        assert client.lookup_domain(str(domain.name)).uuid == domain.uuid


def test_missing_domain_raises_the_specific_error(client: LibvirtClient) -> None:
    with pytest.raises(NoDomainError):
        client.lookup_domain("this-domain-does-not-exist")


def test_other_resources_are_listed_through_their_own_daemons(
    client: LibvirtClient,
) -> None:
    networks = client.list_networks()
    pools = client.list_pools()

    assert all(network.name for network in networks)
    assert all(pool.name for pool in pools)
    assert isinstance(client.list_node_devices(), list)
    assert isinstance(client.list_nwfilters(), list)


def test_async_client_runs_calls_concurrently() -> None:
    import asyncio

    from libvirtpy.client import AsyncLibvirtClient

    async def scenario() -> tuple[int, list[str], list[str]]:
        client = await AsyncLibvirtClient.open("qemu:///system")
        async with client:
            version, networks, pools = await asyncio.gather(
                client.get_version(), client.list_networks(), client.list_pools()
            )
            return (
                version,
                [n.name for n in networks if n.name],
                [p.name for p in pools if p.name],
            )

    try:
        version, networks, pools = asyncio.run(scenario())
    except (ConnectionError, OSError) as error:
        pytest.skip(f"no libvirt daemon to talk to: {error}")

    assert version > 0
    assert isinstance(networks, list)
    assert isinstance(pools, list)
