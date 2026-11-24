"""Read-only checks of the wider set of operations against this machine's daemon.

Run with ``pytest -m libvirt``. Nothing here changes the host. Operations that
need a running domain are checked for libvirt's own refusal when the domain is
stopped, which proves the request was understood.
"""

from collections.abc import Iterator

import pytest

from libvirtpy.client import LibvirtClient
from libvirtpy.rpc.errors import NoSnapshotError, OperationInvalidError

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


@pytest.fixture(scope="module")
def stopped(client: LibvirtClient) -> str:
    """The name of a domain that is not running, or skip."""
    for domain in client.list_domains(active=False):
        if domain.name:
            return domain.name
    pytest.skip("this host has no stopped domain")


def test_driver_information(client: LibvirtClient) -> None:
    assert client.get_driver_type()
    assert client.get_uri().startswith("qemu:")
    assert client.get_library_version() > 0
    assert client.get_max_vcpus() > 0
    assert client.get_cpu_model_names("x86_64")


def test_host_information(client: LibvirtClient) -> None:
    info = client.get_host_info()

    assert info.cpus > 0
    assert info.memory > 0
    assert client.get_host_free_memory() > 0
    assert "total" in client.get_host_memory_stats()
    assert "kernel" in client.get_host_cpu_stats()
    assert client.get_host_cpu_map().online > 0
    assert "shm_sleep_millisecs" in client.get_host_memory_parameters()


def test_statistics_of_all_domains(client: LibvirtClient) -> None:
    statistics = client.get_all_domain_stats()

    assert set(statistics) >= {d.name for d in client.list_domains() if d.name}
    assert all("state.state" in values for values in statistics.values())


def test_domain_facts_of_a_stopped_domain(client: LibvirtClient, stopped: str) -> None:
    assert client.is_domain_active(stopped) is False
    assert client.is_domain_persistent(stopped) is True
    assert client.get_domain_max_memory(stopped) > 0
    assert client.get_domain_os_type(stopped) == "hvm"
    assert client.get_domain_vcpu_count(stopped) > 0
    assert client.has_domain_managed_save(stopped) is False


def test_domain_tuning_parameters_come_back_as_dicts(
    client: LibvirtClient, stopped: str
) -> None:
    assert client.get_domain_scheduler_type(stopped) == "posix"
    assert "cpu_shares" in client.get_domain_scheduler_parameters(stopped)
    assert "hard_limit" in client.get_domain_memory_parameters(stopped)
    assert "weight" in client.get_domain_blkio_parameters(stopped)
    assert "numa_mode" in client.get_domain_numa_parameters(stopped)


def test_running_only_operations_are_refused_by_libvirt(
    client: LibvirtClient, stopped: str
) -> None:
    with pytest.raises(OperationInvalidError):
        client.get_domain_max_vcpus(stopped)
    with pytest.raises(OperationInvalidError):
        client.get_domain_job_stats(stopped)


def test_snapshots_and_checkpoints_of_a_domain(
    client: LibvirtClient, stopped: str
) -> None:
    assert client.list_domain_checkpoints(stopped) == []
    assert client.has_domain_current_snapshot(stopped) in (True, False)
    if not client.has_domain_current_snapshot(stopped):
        with pytest.raises(NoSnapshotError):
            client.get_current_domain_snapshot(stopped)


def test_network_facts(client: LibvirtClient) -> None:
    names = [network.name for network in client.list_networks() if network.name]
    if not names:
        pytest.skip("this host has no network")

    assert client.get_network_bridge_name(names[0])
    assert client.is_network_active(names[0]) in (True, False)
    assert isinstance(client.list_network_dhcp_leases(names[0]), list)
    assert isinstance(client.list_network_ports(names[0]), list)


def test_storage_facts(client: LibvirtClient) -> None:
    pools = [pool.name for pool in client.list_pools(active=True) if pool.name]
    if not pools:
        pytest.skip("this host has no active storage pool")

    info = client.get_pool_info(pools[0])

    assert info.capacity > 0
    assert client.is_pool_active(pools[0]) is True
    for volume in client.list_pool_volumes(pools[0])[:1]:
        assert volume.name
        assert client.get_pool_volume_path(pools[0], volume.name)
        assert client.get_pool_volume_info(pools[0], volume.name).capacity >= 0


def test_node_device_facts(client: LibvirtClient) -> None:
    devices = client.list_node_devices()

    assert devices
    assert client.list_node_device_capabilities(devices[0]) is not None
