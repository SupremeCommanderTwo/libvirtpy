"""Every document this machine's daemon produces survives a round trip.

Run with ``pytest -m libvirt``; read-only.
"""

from collections.abc import Iterator

import pytest

from libvirtpy.client import LibvirtClient
from libvirtpy.rpc.errors import LibvirtError
from libvirtpy.xml import Domain
from libvirtpy.xml.capabilities import (
    Capabilities,
    DomainCapabilities,
    StoragePoolCapabilities,
)
from libvirtpy.xml.interface import HostInterface
from libvirtpy.xml.network import Network
from libvirtpy.xml.nodedev import Device
from libvirtpy.xml.nwfilter import Filter
from libvirtpy.xml.secret import Secret
from libvirtpy.xml.snapshot import Snapshot
from libvirtpy.xml.storage import Pool, Volume
from libvirtpy.xml.sysinfo import Sysinfo
from tests.live.roundtrip import Document, listing, problems, xml_of

pytestmark = pytest.mark.libvirt

# virDomainXMLFlags: secure, inactive, update CPU, migratable.
DOMAIN_VARIANTS = (0, 1, 2, 3, 4, 8, 10)


@pytest.fixture(scope="module")
def client() -> Iterator[LibvirtClient]:
    try:
        connection = LibvirtClient.open("qemu:///system")
    except (ConnectionError, OSError) as error:
        pytest.skip(f"no libvirt daemon to talk to: {error}")
    with connection:
        yield connection


def test_domains_and_their_snapshots(client: LibvirtClient) -> None:
    documents = []
    for handle in listing(client, "connect_list_all_domains"):
        for flags in DOMAIN_VARIANTS:
            xml = xml_of(client, "domain_get_xml_desc", dom=handle, flags=flags)
            documents.append(Document(f"{handle.name} flags={flags}", xml, Domain))
        for snap in listing(client, "domain_list_all_snapshots", dom=handle):
            xml = xml_of(client, "domain_snapshot_get_xml_desc", snap=snap, flags=0)
            documents.append(Document(f"{handle.name}/{snap.name}", xml, Snapshot))

    assert problems(documents) == []


def test_networks_pools_and_volumes(client: LibvirtClient) -> None:
    documents = []
    for handle in listing(client, "connect_list_all_networks"):
        for flags in (0, 1):
            xml = xml_of(client, "network_get_xml_desc", net=handle, flags=flags)
            documents.append(Document(f"network {handle.name} {flags}", xml, Network))
    for handle in listing(client, "connect_list_all_storage_pools"):
        xml = xml_of(client, "storage_pool_get_xml_desc", pool=handle, flags=0)
        documents.append(Document(f"pool {handle.name}", xml, Pool))
        try:
            volumes = listing(client, "storage_pool_list_all_volumes", pool=handle)
        except LibvirtError:
            continue
        for volume in volumes:
            xml = xml_of(client, "storage_vol_get_xml_desc", vol=volume, flags=0)
            documents.append(
                Document(f"volume {handle.name}/{volume.name}", xml, Volume)
            )

    assert problems(documents) == []


def test_host_devices_filters_interfaces_and_secrets(client: LibvirtClient) -> None:
    documents = []
    for handle in listing(client, "connect_list_all_node_devices"):
        xml = xml_of(client, "node_device_get_xml_desc", name=handle, flags=0)
        documents.append(Document(f"device {handle.name}", xml, Device))
    for handle in listing(client, "connect_list_all_nwfilters"):
        xml = xml_of(client, "nwfilter_get_xml_desc", nwfilter=handle, flags=0)
        documents.append(Document(f"filter {handle.name}", xml, Filter))
    for handle in listing(client, "connect_list_all_interfaces"):
        for flags in (0, 1):
            xml = xml_of(client, "interface_get_xml_desc", iface=handle, flags=flags)
            documents.append(
                Document(f"interface {handle.name} {flags}", xml, HostInterface)
            )
    for handle in listing(client, "connect_list_all_secrets"):
        xml = xml_of(client, "secret_get_xml_desc", secret=handle, flags=0)
        documents.append(Document(f"secret {handle.name}", xml, Secret))

    assert problems(documents) == []


def test_host_and_hypervisor_capabilities(client: LibvirtClient) -> None:
    documents = [
        Document(
            "host capabilities",
            xml_of(client, "connect_get_capabilities"),
            Capabilities,
        ),
        Document("sysinfo", xml_of(client, "connect_get_sysinfo", flags=0), Sysinfo),
        Document(
            "pool capabilities",
            xml_of(client, "connect_get_storage_pool_capabilities", flags=0),
            StoragePoolCapabilities,
        ),
    ]
    for virt_type in ("kvm", "qemu"):
        for arch, machine in [(None, None), ("x86_64", "q35"), ("x86_64", "pc")]:
            try:
                xml = xml_of(
                    client,
                    "connect_get_domain_capabilities",
                    emulatorbin=None,
                    arch=arch,
                    machine=machine,
                    virttype=virt_type,
                    flags=0,
                )
            except LibvirtError:
                continue
            documents.append(
                Document(f"{virt_type}/{arch}/{machine}", xml, DomainCapabilities)
            )

    assert problems(documents) == []
