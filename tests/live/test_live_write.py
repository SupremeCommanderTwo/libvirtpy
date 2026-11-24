"""Creating, changing and removing objects on the real system qemu.

Run with ``pytest -m libvirt_write``. Everything is a throwaway ``lvxtest-*``
object (see ``scratch.py``) that is removed at the end of each test; the machine's
own domains, networks and pools are never touched. The disks are a few MiB and
sparse, because the host has little free space.
"""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from libvirtpy.client import DomainLifecycle, DomainState, LibvirtClient
from libvirtpy.client.transport import Request
from libvirtpy.rpc.errors import NoDomainError
from libvirtpy.rpc.subscription import Subscription
from tests.live.roundtrip import fetch, listing
from tests.live.scratch import PREFIX, Scratch
from tests.live.xml_fixtures import EXOTIC_DOMAINS, EXOTIC_TOP, RICH_DOMAIN

pytestmark = pytest.mark.libvirt_write

DOMAIN_FLAGS_CONFIG, DOMAIN_FLAGS_LIVE = 2, 1
SUBNET = "192.168.231"


@pytest.fixture
def scratch() -> Iterator[Scratch]:
    """A registry of throwaway objects, cleaned up after the test."""
    try:
        client = LibvirtClient.open("qemu:///system")
    except (ConnectionError, OSError) as error:
        pytest.skip(f"no libvirt daemon to talk to: {error}")

    registry = Scratch(client)
    try:
        yield registry
    finally:
        registry.cleanup()
        leftovers = registry.leftovers()
        client.close()
        assert not leftovers, f"test objects left behind: {leftovers}"


def minimal_domain(name: str, disk: str | None = None) -> str:
    """Make the XML of a tiny KVM guest that has nothing to boot."""
    disks = ""
    if disk:
        disks = (
            "<disk type='file' device='disk'><driver name='qemu' type='qcow2'/>"
            f"<source file='{disk}'/><target dev='vda' bus='virtio'/></disk>"
        )
    return (
        f"<domain type='kvm'><name>{name}</name><memory unit='MiB'>64</memory>"
        "<vcpu>1</vcpu><os><type arch='x86_64' machine='q35'>hvm</type></os>"
        f"<devices>{disks}<graphics type='vnc' port='-1'/></devices></domain>"
    )


def test_domain_lifecycle(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("vm")
    scratch.domains.append(name)

    defined = client.define_domain(minimal_domain(name))
    started = client.start_domain(name)

    assert defined.uuid
    assert defined.id is None
    assert started.id is not None
    assert client.get_domain_state(name) == DomainState.RUNNING
    assert client.is_domain_active(name) is True
    assert client.get_domain_info(name).vcpus == 1

    client.suspend_domain(name)
    assert client.get_domain_state(name) == DomainState.PAUSED
    client.resume_domain(name)
    assert client.get_domain_state(name) == DomainState.RUNNING

    client.destroy_domain(name)
    assert client.get_domain_state(name) == DomainState.SHUTOFF
    client.undefine_domain(name)
    with pytest.raises(NoDomainError):
        client.lookup_domain(name)


def test_running_domain_facts_and_tuning(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("vm")
    scratch.domains.append(name)
    client.define_domain(minimal_domain(name))
    client.start_domain(name)

    assert client.get_domain_max_vcpus(name) == 1
    (vcpu,) = client.get_domain_vcpus(name)
    assert vcpu.number == 0
    assert vcpu.pinned_to
    assert "cpu_time" in client.get_domain_cpu_stats(name)[0]
    assert client.get_domain_memory_stats(name)
    assert client.get_domain_job_stats(name).type == 0

    client.set_domain_scheduler_parameters(
        name, {"cpu_shares": 512}, flags=DOMAIN_FLAGS_LIVE
    )
    assert client.get_domain_scheduler_parameters(name)["cpu_shares"] == 512

    client.pin_domain_vcpu(name, 0, [0, 1], flags=DOMAIN_FLAGS_LIVE)
    assert client.get_domain_vcpu_pins(name, flags=DOMAIN_FLAGS_LIVE) == [[0, 1]]

    client.set_domain_memory_parameters(
        name, {"soft_limit": 1048576}, flags=DOMAIN_FLAGS_LIVE
    )
    assert client.get_domain_memory_parameters(name)["soft_limit"] == 1048576

    client.set_domain_metadata(name, 1, "a title", flags=3)
    assert client.get_domain_metadata(name, 1) == "a title"


def test_domain_edits_while_stopped(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("vm")
    renamed = scratch.name("renamed")
    scratch.domains += [name, renamed]
    client.define_domain(minimal_domain(name))

    client.set_domain_autostart(name, True)
    assert client.get_domain_autostart(name) is True
    client.set_domain_autostart(name, False)
    client.set_domain_vcpus(name, 1, flags=DOMAIN_FLAGS_CONFIG)
    client.set_domain_max_memory(name, 131072)
    assert client.get_domain_max_memory(name) == 131072

    client.rename_domain(name, renamed)
    assert client.lookup_domain(renamed).name == renamed
    with pytest.raises(NoDomainError):
        client.lookup_domain(name)


def test_managed_save_and_restore(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("vm")
    scratch.domains.append(name)
    client.define_domain(minimal_domain(name))
    client.start_domain(name)

    client.save_domain_managed(name)
    assert client.has_domain_managed_save(name) is True
    assert client.get_domain_state(name) == DomainState.SHUTOFF
    assert client.get_domain_managed_save_xml(name).name == name

    client.start_domain(name)
    assert client.get_domain_state(name) == DomainState.RUNNING
    assert client.has_domain_managed_save(name) is False


def test_isolated_network(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("net")
    scratch.networks.append(name)
    xml = (
        f"<network><name>{name}</name><bridge name='lvxbr0' stp='on' delay='0'/>"
        f"<ip address='{SUBNET}.1' netmask='255.255.255.0'><dhcp>"
        f"<range start='{SUBNET}.10' end='{SUBNET}.20'/></dhcp></ip></network>"
    )

    defined = client.define_network(xml)
    started = client.start_network(name)

    assert defined.uuid
    assert started.name == name
    assert client.is_network_active(name) is True
    assert client.is_network_persistent(name) is True
    assert client.get_network_bridge_name(name) == "lvxbr0"
    assert client.list_network_dhcp_leases(name) == []

    client.update_network(
        name,
        command=3,
        section=4,
        xml=f"<host mac='52:54:00:12:34:56' ip='{SUBNET}.11'/>",
        flags=DOMAIN_FLAGS_LIVE | DOMAIN_FLAGS_CONFIG,
    )
    assert client.lookup_network(name).ips[0].dhcp is not None

    client.set_network_autostart(name, True)
    assert client.get_network_autostart(name) is True
    client.set_network_autostart(name, False)
    client.set_network_metadata(name, 1, "test network", flags=3)
    assert client.get_network_metadata(name, 1) == "test network"

    client.destroy_network(name)
    assert client.is_network_active(name) is False
    client.undefine_network(name)


def pool_xml(name: str, path: str) -> str:
    """Make the XML of a directory pool."""
    target = f"<target><path>{path}</path></target>"
    return f"<pool type='dir'><name>{name}</name>{target}</pool>"


def volume_xml(name: str, megabytes: int, kind: str = "raw") -> str:
    """Make the XML of a small sparse volume."""
    return (
        f"<volume><name>{name}</name><capacity unit='MiB'>{megabytes}</capacity>"
        f"<allocation unit='B'>0</allocation>"
        f"<target><format type='{kind}'/></target></volume>"
    )


def test_storage_pool_and_volumes(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("pool")
    path = f"/var/tmp/{name}"
    scratch.pools.append(name)

    client.define_pool(pool_xml(name, path))
    client.build_pool(name)
    client.start_pool(name)

    assert client.is_pool_active(name) is True
    assert client.lookup_pool_by_target_path(path).name == name
    assert client.get_pool_info(name).capacity > 0

    first = client.create_pool_volume(name, volume_xml("a.img", 4))
    assert first.key
    assert client.get_pool_volume_path(name, "a.img") == f"{path}/a.img"
    assert client.get_pool_volume_info(name, "a.img").capacity == 4 * 1024 * 1024
    assert client.lookup_pool_by_volume(name, "a.img").name == name

    clone = client.create_pool_volume_from(name, volume_xml("b.img", 4), "a.img")
    assert clone.name == "b.img"
    client.resize_pool_volume(name, "b.img", 8 * 1024 * 1024)
    assert client.get_pool_volume_info(name, "b.img").capacity == 8 * 1024 * 1024
    client.wipe_pool_volume_with_pattern(name, "b.img", 0)
    client.refresh_pool(name)

    assert sorted(v.name for v in client.list_pool_volumes(name)) == ["a.img", "b.img"]
    client.delete_pool_volume(name, "a.img")
    client.delete_pool_volume(name, "b.img")
    client.destroy_pool(name)
    client.delete_pool(name)
    client.undefine_pool(name)
    assert not Path(path).exists()


def test_disk_operations_on_a_running_domain(scratch: Scratch) -> None:
    client, pool, name = scratch.client, scratch.name("pool"), scratch.name("vm")
    path = f"/var/tmp/{pool}"
    scratch.pools.append(pool)
    scratch.domains.append(name)
    client.define_pool(pool_xml(pool, path))
    client.build_pool(pool)
    client.start_pool(pool)
    disk = client.create_pool_volume(pool, volume_xml("d.qcow2", 8, "qcow2"))
    assert disk.target is not None and disk.target.path
    client.define_domain(minimal_domain(name, disk.target.path))
    client.start_domain(name)

    info = client.get_domain_block_info(name, "vda")
    assert info.capacity == 8 * 1024 * 1024
    assert "rd_operations" in client.get_domain_block_stats(name, "vda")

    client.resize_domain_block(name, "vda", 16 * 1024 * 1024, flags=1)
    assert client.get_domain_block_info(name, "vda").capacity == 16 * 1024 * 1024

    client.set_domain_block_io_tune(
        name, "vda", {"total_bytes_sec": 10_000_000}, flags=DOMAIN_FLAGS_LIVE
    )
    tune = client.get_domain_block_io_tune(name, "vda", flags=DOMAIN_FLAGS_LIVE)
    assert tune["total_bytes_sec"] == 10_000_000
    assert client.get_domain_disk_errors(name) == []


def test_secret_and_network_filter(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("filter")
    scratch.filters.append(name)
    xml = (
        f"<filter name='{name}' chain='root'>"
        "<rule action='drop' direction='in' priority='500'>"
        "<tcp dstportstart='23'/></rule></filter>"
    )

    created = client.define_nwfilter(xml)

    assert created.name == name
    assert client.lookup_nwfilter(name).uuid == created.uuid
    client.undefine_nwfilter(name)
    scratch.filters.clear()

    secret = client.define_secret(
        "<secret ephemeral='yes' private='no'><description>lvxtest</description>"
        "<usage type='volume'><volume>/var/tmp/lvxtest-secret</volume></usage></secret>"
    )
    scratch.secrets.append(str(secret.uuid))
    client.set_secret_value(str(secret.uuid), b"s3cret")
    assert client.get_secret_value(str(secret.uuid)) == b"s3cret"
    assert (
        client.lookup_secret_by_usage(1, "/var/tmp/lvxtest-secret").uuid == secret.uuid
    )


def test_the_scratch_registry_refuses_foreign_names(scratch: Scratch) -> None:
    with pytest.raises(AssertionError, match="refusing"):
        scratch._remove_domain("an-existing-vm")
    assert PREFIX == "lvxtest-"


def running_domain_with_disk(scratch: Scratch) -> tuple[str, str, str]:
    """Create a pool, a qcow2 volume and a running domain that boots from it.

    :returns: the domain name, the pool name and the pool's directory.
    """
    client = scratch.client
    pool, name = scratch.name("pool"), scratch.name("vm")
    path = f"/var/tmp/{pool}"
    scratch.pools.append(pool)
    scratch.domains.append(name)

    client.define_pool(pool_xml(pool, path))
    client.build_pool(pool)
    client.start_pool(pool)
    disk = client.create_pool_volume(pool, volume_xml("d.qcow2", 8, "qcow2"))
    assert disk.target is not None and disk.target.path
    client.define_domain(minimal_domain(name, disk.target.path))
    client.start_domain(name)
    return name, pool, path


def snapshot_xml(name: str, file: str) -> str:
    """Make the XML of a disk-only external snapshot of ``vda``."""
    return (
        f"<domainsnapshot><name>{name}</name><disks>"
        f"<disk name='vda' snapshot='external'><source file='{file}'/></disk>"
        "</disks></domainsnapshot>"
    )


def test_external_snapshots_and_active_commit(scratch: Scratch) -> None:
    client = scratch.client
    name, _, path = running_domain_with_disk(scratch)
    disk_only = 16

    first = client.create_domain_snapshot(
        name, snapshot_xml("s1", f"{path}/s1.qcow2"), flags=disk_only
    )
    second = client.create_domain_snapshot(
        name, snapshot_xml("s2", f"{path}/s2.qcow2"), flags=disk_only
    )

    assert first.name == "s1"
    assert second.parent is not None and second.parent.name == "s1"
    assert sorted(str(s.name) for s in client.list_domain_snapshots(name)) == [
        "s1",
        "s2",
    ]
    assert client.get_current_domain_snapshot(name).name == "s2"
    assert client.is_domain_snapshot_current(name, "s2") is True
    assert client.get_domain_snapshot_parent(name, "s2").name == "s1"
    assert [s.name for s in client.list_domain_snapshot_children(name, "s1")] == ["s2"]

    commit_active, pivot = 4, 2
    client.commit_domain_block(name, "vda", flags=commit_active)
    wait_for_block_job(client, name)
    client.abort_domain_block_job(name, "vda", flags=pivot)

    metadata_only = 2
    client.delete_domain_snapshot(name, "s2", flags=metadata_only)
    client.delete_domain_snapshot(name, "s1", flags=metadata_only)
    assert client.list_domain_snapshots(name) == []


def wait_for_block_job(client: LibvirtClient, name: str) -> None:
    """Wait until the block job of ``vda`` has copied everything (it is ready)."""
    import time

    for _ in range(50):
        job = client.get_domain_block_job_info(name, "vda")
        if job.found and job.cur == job.end:
            return
        time.sleep(0.1)
    raise AssertionError("the block job did not become ready")


def test_checkpoints_and_backup(scratch: Scratch) -> None:
    client = scratch.client
    name, _, path = running_domain_with_disk(scratch)
    checkpoint = (
        "<domaincheckpoint><name>c1</name><disks>"
        "<disk name='vda' checkpoint='bitmap'/></disks></domaincheckpoint>"
    )

    created = client.create_domain_checkpoint(name, checkpoint)

    assert created.name == "c1"
    assert [c.name for c in client.list_domain_checkpoints(name)] == ["c1"]
    assert client.lookup_domain_checkpoint(name, "c1").name == "c1"

    backup = (
        "<domainbackup mode='pull'><server transport='unix' "
        f"socket='/run/libvirt/qemu/{name}-backup.sock'/>"
        "<disks><disk name='vda' type='file'>"
        f"<scratch file='{path}/scratch.qcow2'/></disk></disks></domainbackup>"
    )
    client.begin_domain_backup(name, backup)
    try:
        assert client.get_domain_backup(name).mode == "pull"
    finally:
        client.abort_domain_backup(name)

    client.delete_domain_checkpoint(name, "c1")
    assert client.list_domain_checkpoints(name) == []


def test_interfaces_ports_and_hotplug(scratch: Scratch) -> None:
    client, network, name = scratch.client, scratch.name("net"), scratch.name("vm")
    scratch.networks.append(network)
    scratch.domains.append(name)
    client.define_network(
        f"<network><name>{network}</name><bridge name='lvxbr1' stp='on' delay='0'/>"
        f"<ip address='{SUBNET}.129' netmask='255.255.255.128'/></network>"
    )
    client.start_network(network)
    client.define_domain(minimal_domain(name))
    client.start_domain(name)
    nic = (
        f"<interface type='network'><source network='{network}'/>"
        "<mac address='52:54:00:aa:bb:cc'/><model type='virtio'/></interface>"
    )

    client.attach_domain_device(name, nic, flags=DOMAIN_FLAGS_LIVE)

    ports = client.list_network_ports(network)
    assert len(ports) == 1
    assert ports[0].uuid
    assert client.lookup_network_port(network, ports[0]).uuid == ports[0].uuid
    stats = client.get_domain_interface_stats(name, "52:54:00:aa:bb:cc")
    assert stats.rx_bytes >= 0

    client.set_domain_interface_parameters(
        name, "52:54:00:aa:bb:cc", {"inbound.average": 500}, flags=DOMAIN_FLAGS_LIVE
    )
    limits = client.get_domain_interface_parameters(
        name, "52:54:00:aa:bb:cc", flags=DOMAIN_FLAGS_LIVE
    )
    assert limits["inbound.average"] == 500

    client.detach_domain_device(name, nic, flags=DOMAIN_FLAGS_LIVE)


def test_save_to_a_file_and_restore(scratch: Scratch) -> None:
    client, pool, name = scratch.client, scratch.name("pool"), scratch.name("vm")
    path = f"/var/tmp/{pool}"
    scratch.pools.append(pool)
    scratch.domains.append(name)
    client.define_pool(pool_xml(pool, path))
    client.build_pool(pool)
    client.start_pool(pool)
    client.define_domain(minimal_domain(name))
    client.start_domain(name)
    file = f"{path}/state.save"

    client.save_domain(name, file)

    assert client.get_domain_state(name) == DomainState.SHUTOFF
    assert client.get_saved_domain_xml(file).name == name
    client.restore_domain(file)
    assert client.get_domain_state(name) == DomainState.RUNNING


def test_guest_keys_nmi_and_lifecycle_actions(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("vm")
    scratch.domains.append(name)
    client.define_domain(minimal_domain(name))
    client.start_domain(name)

    client.send_domain_keys(name, [30], holdtime=50)
    client.inject_domain_nmi(name)
    client.set_domain_lifecycle_action(name, 0, 0, flags=DOMAIN_FLAGS_LIVE)
    client.set_domain_memory(name, 32768, flags=DOMAIN_FLAGS_LIVE)
    assert client.get_domain_info(name).memory_kib <= 65536


def test_lifecycle_events_of_a_domain(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("vm")
    scratch.domains.append(name)

    with client.events("domain", target=None) as events:
        client.define_domain(minimal_domain(name))
        client.start_domain(name)
        client.suspend_domain(name)
        client.resume_domain(name)
        client.destroy_domain(name)
        seen = lifecycle_of(events, name, until=DomainLifecycle.STOPPED)

    assert seen[:5] == [
        DomainLifecycle.DEFINED,
        DomainLifecycle.STARTED,
        DomainLifecycle.SUSPENDED,
        DomainLifecycle.RESUMED,
        DomainLifecycle.STOPPED,
    ] or {DomainLifecycle.STARTED, DomainLifecycle.STOPPED} <= set(seen)
    assert DomainLifecycle.SUSPENDED in seen
    assert DomainLifecycle.DEFINED in seen


def lifecycle_of(
    events: Subscription, name: str, until: DomainLifecycle
) -> list[DomainLifecycle]:
    """Collect the lifecycle events of one domain until ``until`` is seen."""
    seen: list[DomainLifecycle] = []
    for _ in range(20):
        event = events.get(timeout=5)
        if event.name != name or event.lifecycle is None:
            continue
        seen.append(event.lifecycle[0])
        if event.lifecycle[0] == until:
            break
    return seen


def test_events_filtered_to_one_domain_and_one_network(scratch: Scratch) -> None:
    client = scratch.client
    quiet, busy, network = scratch.name("vm"), scratch.name("vm"), scratch.name("net")
    scratch.domains += [quiet, busy]
    scratch.networks.append(network)
    client.define_domain(minimal_domain(quiet))
    client.define_domain(minimal_domain(busy))

    network_xml = (
        f"<network><name>{network}</name><bridge name='lvxbr2' stp='on' delay='0'/>"
        f"<ip address='{SUBNET}.193' netmask='255.255.255.192'/></network>"
    )
    with (
        client.events("domain", target=busy) as domain_events,
        client.events("network", target=None) as network_events,
    ):
        client.start_domain(quiet)
        client.start_domain(busy)
        client.define_network(network_xml)
        client.start_network(network)
        seen = lifecycle_of(domain_events, busy, until=DomainLifecycle.STARTED)
        network_event = network_events.get(timeout=5)
        while network_event.name != network:
            network_event = network_events.get(timeout=5)

    assert DomainLifecycle.STARTED in seen
    assert network_event.source == "network"
    assert network_event.kind == "lifecycle"


def test_volume_upload_and_download_round_trip(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("pool")
    path = f"/var/tmp/{name}"
    scratch.pools.append(name)
    client.define_pool(pool_xml(name, path))
    client.build_pool(name)
    client.start_pool(name)
    client.create_pool_volume(name, volume_xml("data.img", 1))
    payload = bytes(range(256)) * 400

    with client.upload_pool_volume(name, "data.img", 0, len(payload)) as target:
        assert target.write(payload) == len(payload)

    with client.download_pool_volume(name, "data.img", 0, len(payload)) as source:
        downloaded = source.read()
    assert downloaded == payload

    with client.download_pool_volume(name, "data.img", 256, 512) as source:
        assert source.read() == payload[256:768]


def test_volume_transfer_with_the_async_client(scratch: Scratch) -> None:
    import asyncio

    from libvirtpy.client import AsyncLibvirtClient

    client, name = scratch.client, scratch.name("pool")
    path = f"/var/tmp/{name}"
    scratch.pools.append(name)
    client.define_pool(pool_xml(name, path))
    client.build_pool(name)
    client.start_pool(name)
    client.create_pool_volume(name, volume_xml("async.img", 1))
    payload = b"async " * 10000

    async def transfer() -> bytes:
        async with await AsyncLibvirtClient.open("qemu:///system") as other:
            async with await other.upload_pool_volume(
                name, "async.img", 0, len(payload)
            ) as target:
                await target.write(payload)
            async with await other.download_pool_volume(
                name, "async.img", 0, len(payload)
            ) as source:
                return await source.read()

    assert asyncio.run(transfer()) == payload


def test_screenshot_of_a_running_domain(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("vm")
    scratch.domains.append(name)
    client.define_domain(minimal_domain(name))
    client.start_domain(name)

    with client.take_domain_screenshot(name) as image:
        mime = image.reply
        data = image.read()

    assert mime in ("image/x-portable-pixmap", "image/png")
    assert data.startswith((b"P6", b"\x89PNG"))
    assert len(data) > 100


def test_console_and_channel_of_a_running_domain(scratch: Scratch) -> None:
    client, name = scratch.client, scratch.name("vm")
    scratch.domains.append(name)
    client.define_domain(
        minimal_domain(name).replace(
            "<graphics",
            "<console type='pty'><target type='serial' port='0'/></console>"
            "<channel type='unix'><target type='virtio' "
            "name='org.qemu.guest_agent.0'/></channel><graphics",
        )
    )
    client.start_domain(name)

    with client.open_domain_console(name) as console:
        console.write(b"\n")
        assert console.readable() and console.writable()

    with client.open_domain_channel(name, "org.qemu.guest_agent.0") as channel:
        assert channel.writable()


def test_the_xml_of_a_running_domain_and_its_objects_round_trips(
    scratch: Scratch,
) -> None:
    from libvirtpy.xml import Domain
    from libvirtpy.xml.backup import Backup, Checkpoint
    from libvirtpy.xml.network import Network, NetworkPort
    from libvirtpy.xml.snapshot import Snapshot
    from libvirtpy.xml.storage import Pool, Volume
    from tests.live.roundtrip import Document, problems

    client, pool, network, name = (
        scratch.client,
        scratch.name("pool"),
        scratch.name("net"),
        scratch.name("vm"),
    )
    path = f"/var/tmp/{pool}"
    scratch.pools.append(pool)
    scratch.networks.append(network)
    scratch.domains.append(name)
    client.define_pool(pool_xml(pool, path))
    client.build_pool(pool)
    client.start_pool(pool)
    disk = client.create_pool_volume(pool, volume_xml("a.qcow2", 8, "qcow2"))
    assert disk.target is not None and disk.target.path
    client.define_network(
        f"<network><name>{network}</name><bridge name='lvxbr3' stp='on' delay='0'/>"
        f"<forward mode='nat'/><ip address='{SUBNET}.65' netmask='255.255.255.192'>"
        f"<dhcp><range start='{SUBNET}.70' end='{SUBNET}.80'/></dhcp></ip></network>"
    )
    client.start_network(network)
    client.define_domain(
        RICH_DOMAIN.format(name=name, disk=disk.target.path, network=network)
    )
    client.start_domain(name)
    handle = fetch(client, "domain_lookup_by_name", name=name)
    documents = []

    def get(procedure: str, **arguments: object) -> str:
        reply = client._transport.call(Request(procedure, arguments))
        assert isinstance(reply, str)
        return reply

    for flags in (0, 1, 2, 4, 8):
        xml = get("domain_get_xml_desc", dom=handle, flags=flags)
        documents.append(Document(f"domain flags={flags}", xml, Domain))
    network_handle = fetch(client, "network_lookup_by_name", name=network)
    documents.append(
        Document(
            "network", get("network_get_xml_desc", net=network_handle, flags=0), Network
        )
    )
    for port in listing(client, "network_list_all_ports", network=network_handle):
        documents.append(
            Document(
                "port",
                get("network_port_get_xml_desc", port=port, flags=0),
                NetworkPort,
            )
        )
    documents.append(
        Document("pool", str(client.lookup_pool(pool).to_xml(encoding="unicode")), Pool)
    )
    for volume in client.list_pool_volumes(pool):
        documents.append(
            Document(
                f"volume {volume.name}", str(volume.to_xml(encoding="unicode")), Volume
            )
        )

    client.create_domain_checkpoint(
        name,
        "<domaincheckpoint><name>c1</name><description>d</description><disks>"
        "<disk name='vda' checkpoint='bitmap'/></disks></domaincheckpoint>",
    )
    checkpoint_handle = client._transport.call(
        Request(
            "domain_checkpoint_lookup_by_name",
            {"dom": handle, "name": "c1", "flags": 0},
        )
    )
    for flags in (0, 1):
        xml = get(
            "domain_checkpoint_get_xml_desc", checkpoint=checkpoint_handle, flags=flags
        )
        documents.append(Document(f"checkpoint flags={flags}", xml, Checkpoint))

    client.begin_domain_backup(
        name,
        "<domainbackup mode='pull'><server transport='unix' "
        f"socket='/run/libvirt/qemu/{name}-b.sock'/>"
        "<disks><disk name='vda' type='file'>"
        f"<scratch file='{path}/scr.qcow2'/></disk></disks></domainbackup>",
    )
    try:
        documents.append(
            Document(
                "backup", get("domain_backup_get_xml_desc", dom=handle, flags=0), Backup
            )
        )
    finally:
        client.abort_domain_backup(name)

    client.destroy_domain(name)
    client.start_domain(name)
    for snapshot in ("s1", "s2"):
        client.create_domain_snapshot(
            name,
            f"<domainsnapshot><name>{snapshot}</name><description>test</description>"
            "<disks><disk name='vda' snapshot='external'>"
            f"<source file='{path}/{snapshot}.qcow2'/>"
            "</disk></disks></domainsnapshot>",
            flags=16,
        )
    handle = fetch(client, "domain_lookup_by_name", name=name)
    for snap in listing(client, "domain_list_all_snapshots", dom=handle):
        for flags in (0, 1):
            xml = get("domain_snapshot_get_xml_desc", snap=snap, flags=flags)
            documents.append(
                Document(f"snapshot {snap.name} flags={flags}", xml, Snapshot)
            )
    documents.append(
        Document(
            "domain with snapshots",
            get("domain_get_xml_desc", dom=handle, flags=0),
            Domain,
        )
    )

    assert problems(documents) == []


@pytest.mark.parametrize("feature", sorted(EXOTIC_DOMAINS))
def test_the_live_xml_of_unusual_domain_features_round_trips(
    scratch: Scratch, feature: str
) -> None:
    from libvirtpy.xml import Domain
    from tests.live.roundtrip import Document, problems

    if feature == "tpm" and shutil.which("swtpm") is None:
        pytest.skip("swtpm is not installed")
    os_attributes, devices = EXOTIC_DOMAINS[feature]
    client, name = scratch.client, scratch.name("vm")
    scratch.domains.append(name)
    xml = (
        f"<domain type='kvm'><name>{name}</name><memory unit='MiB'>256</memory>"
        f"<vcpu placement='static'>2</vcpu>{EXOTIC_TOP.get(feature, '')}"
        f"<os {os_attributes}><type arch='x86_64' machine='q35'>hvm</type></os>"
        f"<features><acpi/><apic/></features><devices>{devices}"
        "<graphics type='vnc' port='-1'/></devices></domain>"
    )

    client.define_domain(xml)
    client.start_domain(name)
    handle = fetch(client, "domain_lookup_by_name", name=name)
    documents = []
    for flags in (0, 1, 2):
        reply = fetch(client, "domain_get_xml_desc", dom=handle, flags=flags)
        assert isinstance(reply, str)
        documents.append(Document(f"{feature} flags={flags}", reply, Domain))

    assert problems(documents) == []
