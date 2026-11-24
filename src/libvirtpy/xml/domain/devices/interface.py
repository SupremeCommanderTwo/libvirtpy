"""``<interface>``: network interfaces.

One class per interface ``type`` (each has its own ``<source>``); ``Interface``
is their plain union (see ``libvirtpy.xml.domain.devices.address`` for why it is
not a discriminated union).

See https://libvirt.org/formatdomain.html#network-interfaces
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.network import Bandwidth, FilterRef, Route, VirtualPort, Vlan
from libvirtpy.xml._types import HexNumber, OnOff, Uuid, YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import (
    Alias,
    DeviceAcpi,
    DeviceBoot,
    VirtioDriverOptions,
)
from libvirtpy.xml.domain.storage_source import Reconnect

__all__ = [
    "Bandwidth",
    "BridgeInterface",
    "ClientInterface",
    "DirectInterface",
    "EthernetInterface",
    "HostdevInterface",
    "Interface",
    "InterfaceBackend",
    "InterfaceDriver",
    "InterfaceMac",
    "InternalInterface",
    "McastInterface",
    "NetworkInterface",
    "NullInterface",
    "ServerInterface",
    "UdpInterface",
    "UserInterface",
    "VdpaInterface",
    "VdsInterface",
    "VhostUserInterface",
]


class InterfaceIp(LibvirtXmlModel, tag="ip"):
    """``<ip>``: an address configured in the guest."""

    address: str = attr(name="address")
    family: str | None = attr(name="family", default=None)
    prefix: int | None = attr(name="prefix", default=None, ge=0)
    peer: str | None = attr(name="peer", default=None)


class InterfaceLink(LibvirtXmlModel, tag="link"):
    state: Literal["up", "down"] = attr(name="state")


class InterfaceMtu(LibvirtXmlModel, tag="mtu"):
    size: int = attr(name="size", ge=0, le=65535)


class CoalesceFrames(LibvirtXmlModel, tag="frames"):
    max: int | None = attr(name="max", default=None, ge=0)


class CoalesceRx(LibvirtXmlModel, tag="rx"):
    frames: CoalesceFrames | None = element(tag="frames", default=None)


class InterfaceCoalesce(LibvirtXmlModel, tag="coalesce"):
    """``<coalesce>``: interrupt coalescing. Since 3.3.0."""

    rx: CoalesceRx | None = element(tag="rx", default=None)


class InterfaceTarget(LibvirtXmlModel, tag="target"):
    """``<target>``: the host side device."""

    dev: str = attr(name="dev")
    managed: YesNo | None = attr(name="managed", default=None)


class InterfaceGuest(LibvirtXmlModel, tag="guest"):
    """``<guest>``: the guest side device name."""

    dev: str | None = attr(name="dev", default=None)
    actual: str | None = attr(name="actual", default=None)


class InterfaceMac(LibvirtXmlModel, tag="mac"):
    """``<mac>``: the MAC address."""

    address: str = attr(name="address")
    type: Literal["generated", "static"] | None = attr(name="type", default=None)
    check: YesNo | None = attr(name="check", default=None)
    current_address: str | None = attr(name="currentAddress", default=None)


class InterfaceScript(LibvirtXmlModel):
    """Base of ``<script>`` and ``<downscript>``."""

    path: str = attr(name="path")


class UpScript(InterfaceScript, tag="script"):
    """``<script>``: run when the interface comes up."""


class DownScript(InterfaceScript, tag="downscript"):
    """``<downscript>``: run when the interface goes down."""


class BackendDomain(LibvirtXmlModel, tag="backenddomain"):
    name: str = attr(name="name")


class InterfaceModel(LibvirtXmlModel, tag="model"):
    """``<model>``: the emulated NIC, e.g. ``virtio`` or ``e1000``."""

    type: str = attr(name="type")


class InterfaceBackend(LibvirtXmlModel, tag="backend"):
    """``<backend>``: the host helper that serves the interface."""

    type: Literal["default", "passt"] | None = attr(name="type", default=None)
    tap: str | None = attr(name="tap", default=None)
    vhost: str | None = attr(name="vhost", default=None)
    log_file: str | None = attr(name="logFile", default=None)
    hostname: str | None = attr(name="hostname", default=None)
    fqdn: str | None = attr(name="fqdn", default=None)


class HostOffloads(LibvirtXmlModel, tag="host"):
    csum: OnOff | None = attr(name="csum", default=None)
    gso: OnOff | None = attr(name="gso", default=None)
    tso4: OnOff | None = attr(name="tso4", default=None)
    tso6: OnOff | None = attr(name="tso6", default=None)
    ecn: OnOff | None = attr(name="ecn", default=None)
    ufo: OnOff | None = attr(name="ufo", default=None)
    mrg_rxbuf: OnOff | None = attr(name="mrg_rxbuf", default=None)


class GuestOffloads(LibvirtXmlModel, tag="guest"):
    csum: OnOff | None = attr(name="csum", default=None)
    tso4: OnOff | None = attr(name="tso4", default=None)
    tso6: OnOff | None = attr(name="tso6", default=None)
    ecn: OnOff | None = attr(name="ecn", default=None)
    ufo: OnOff | None = attr(name="ufo", default=None)


class InterfaceDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>``: tuning of the NIC, or of the passthrough driver."""

    name: Literal["qemu", "vhost", "kvm", "vfio", "xen"] | None = attr(
        name="name", default=None
    )
    model: str | None = attr(name="model", default=None, description="Hostdev only.")
    iommufd: YesNo | None = attr(name="iommufd", default=None)
    queues: int | None = attr(name="queues", default=None, ge=1)
    rx_queue_size: int | None = attr(name="rx_queue_size", default=None, ge=1)
    tx_queue_size: int | None = attr(name="tx_queue_size", default=None, ge=1)
    txmode: Literal["iothread", "timer"] | None = attr(name="txmode", default=None)
    ioeventfd: OnOff | None = attr(name="ioeventfd", default=None)
    event_idx: OnOff | None = attr(name="event_idx", default=None)
    rss: OnOff | None = attr(name="rss", default=None)
    rss_hash_report: OnOff | None = attr(name="rss_hash_report", default=None)
    host: HostOffloads | None = element(tag="host", default=None)
    guest: GuestOffloads | None = element(tag="guest", default=None)


class InterfaceTune(LibvirtXmlModel, tag="tune"):
    """``<tune>``: socket tuning."""

    sndbuf: int | None = element(tag="sndbuf", default=None, ge=0)


class InterfaceRom(LibvirtXmlModel, tag="rom"):
    """``<rom>``: the option ROM of the NIC."""

    enabled: YesNo | None = attr(name="enabled", default=None)
    bar: OnOff | None = attr(name="bar", default=None)
    file: str | None = attr(name="file", default=None)


class InterfacePort(LibvirtXmlModel, tag="port"):
    """``<port>``: port options of the host switch."""

    isolated: YesNo | None = attr(name="isolated", default=None)


class InterfaceTeaming(LibvirtXmlModel, tag="teaming"):
    """``<teaming>``: failover pairing with a hostdev interface. Since 6.1.0."""

    type: Literal["persistent", "transient"] = attr(name="type")
    persistent: str | None = attr(
        name="persistent", default=None, description="Transient only: its pair."
    )


class PortRange(LibvirtXmlModel, tag="range"):
    start: int = attr(name="start", ge=0, le=65535)
    end: int | None = attr(name="end", default=None, ge=0, le=65535)
    to: int | None = attr(name="to", default=None, ge=0, le=65535)
    exclude: YesNo | None = attr(name="exclude", default=None)


class PortForward(LibvirtXmlModel, tag="portForward"):
    """``<portForward>``: host ports forwarded to the guest (passt)."""

    proto: Literal["tcp", "udp"] = attr(name="proto")
    address: str | None = attr(name="address", default=None)
    dev: str | None = attr(name="dev", default=None)
    ranges: list[PortRange] = element(tag="range", default_factory=list)


class _InterfaceBase(LibvirtXmlModel, tag="interface"):
    """Attributes and children every interface type has."""

    trust_guest_rx_filters: YesNo | None = attr(
        name="trustGuestRxFilters", default=None
    )
    managed: YesNo | None = attr(
        name="managed", default=None, description="``type='hostdev'`` only."
    )
    virtualport: VirtualPort | None = element(tag="virtualport", default=None)
    link: InterfaceLink | None = element(tag="link", default=None)
    mtu: InterfaceMtu | None = element(tag="mtu", default=None)
    coalesce: InterfaceCoalesce | None = element(tag="coalesce", default=None)
    target: InterfaceTarget | None = element(tag="target", default=None)
    guest: InterfaceGuest | None = element(tag="guest", default=None)
    mac: InterfaceMac | None = element(tag="mac", default=None)
    ips: list[InterfaceIp] = element(tag="ip", default_factory=list)
    routes: list[Route] = element(tag="route", default_factory=list)
    port_forwards: list[PortForward] = element(tag="portForward", default_factory=list)
    script: UpScript | None = element(tag="script", default=None)
    downscript: DownScript | None = element(tag="downscript", default=None)
    backend_domain: BackendDomain | None = element(tag="backenddomain", default=None)
    model: InterfaceModel | None = element(tag="model", default=None)
    backend: InterfaceBackend | None = element(tag="backend", default=None)
    driver: InterfaceDriver | None = element(tag="driver", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
    filterref: FilterRef | None = element(tag="filterref", default=None)
    tune: InterfaceTune | None = element(tag="tune", default=None)
    boot: DeviceBoot | None = element(tag="boot", default=None)
    rom: InterfaceRom | None = element(tag="rom", default=None)
    bandwidth: Bandwidth | None = element(tag="bandwidth", default=None)
    vlan: Vlan | None = element(tag="vlan", default=None)
    port: InterfacePort | None = element(tag="port", default=None)
    teaming: InterfaceTeaming | None = element(tag="teaming", default=None)


class _NetworkAttributes(LibvirtXmlModel):
    """``<source>`` attributes that name a libvirt network."""

    network: str | None = attr(name="network", default=None)
    portgroup: str | None = attr(name="portgroup", default=None)
    portid: Uuid | None = attr(name="portid", default=None)


class BridgeSource(_NetworkAttributes, tag="source"):
    """``<source bridge=...>`` of a ``type='bridge'`` interface."""

    bridge: str | None = attr(name="bridge", default=None)
    mac_table_manager: Literal["kernel", "libvirt"] | None = attr(
        name="macTableManager", default=None
    )


class BridgeInterface(_InterfaceBase, tag="interface"):
    type: Literal["bridge"] = attr(name="type")
    source: BridgeSource | None = element(tag="source", default=None)


class NetworkSourceInfo(BridgeSource, tag="source"):
    """``<source network=...>`` of a ``type='network'`` interface."""


class NetworkInterface(_InterfaceBase, tag="interface"):
    type: Literal["network"] = attr(name="type")
    source: NetworkSourceInfo | None = element(tag="source", default=None)


class EthernetSource(LibvirtXmlModel, tag="source"):
    """``<source>`` of a ``type='ethernet'`` interface: addresses and routes."""

    ips: list[InterfaceIp] = element(tag="ip", default_factory=list)
    routes: list[Route] = element(tag="route", default_factory=list)


class EthernetInterface(_InterfaceBase, tag="interface"):
    type: Literal["ethernet"] = attr(name="type")
    source: EthernetSource | None = element(tag="source", default=None)


class VhostUserSource(LibvirtXmlModel, tag="source"):
    type: Literal["unix"] | None = attr(name="type", default=None)
    path: str | None = attr(name="path", default=None)
    mode: Literal["server", "client"] | None = attr(name="mode", default=None)
    dev: str | None = attr(name="dev", default=None)
    reconnect: Reconnect | None = element(tag="reconnect", default=None)


class VhostUserInterface(_InterfaceBase, tag="interface"):
    type: Literal["vhostuser"] = attr(name="type")
    source: VhostUserSource | None = element(tag="source", default=None)


class DirectSource(_NetworkAttributes, tag="source"):
    dev: str = attr(name="dev")
    mode: Literal["vepa", "bridge", "private", "passthrough"] | None = attr(
        name="mode", default=None
    )


class DirectInterface(_InterfaceBase, tag="interface"):
    type: Literal["direct"] = attr(name="type")
    source: DirectSource | None = element(tag="source", default=None)


class UserSource(LibvirtXmlModel, tag="source"):
    dev: str = attr(name="dev")


class UserInterface(_InterfaceBase, tag="interface"):
    type: Literal["user"] = attr(name="type")
    source: UserSource | None = element(tag="source", default=None)


class InternalSource(LibvirtXmlModel, tag="source"):
    name: str = attr(name="name")


class InternalInterface(_InterfaceBase, tag="interface"):
    type: Literal["internal"] = attr(name="type")
    source: InternalSource | None = element(tag="source", default=None)


class SocketSource(LibvirtXmlModel, tag="source"):
    """``<source>`` of an ``mcast``/``client``/``server`` interface."""

    address: str | None = attr(name="address", default=None)
    port: int = attr(name="port", ge=0, le=65535)


class McastInterface(_InterfaceBase, tag="interface"):
    type: Literal["mcast"] = attr(name="type")
    source: SocketSource | None = element(tag="source", default=None)


class ClientInterface(_InterfaceBase, tag="interface"):
    type: Literal["client"] = attr(name="type")
    source: SocketSource | None = element(tag="source", default=None)


class ServerInterface(_InterfaceBase, tag="interface"):
    type: Literal["server"] = attr(name="type")
    source: SocketSource | None = element(tag="source", default=None)


class UdpLocal(LibvirtXmlModel, tag="local"):
    address: str = attr(name="address")
    port: int = attr(name="port", ge=0, le=65535)


class UdpSource(LibvirtXmlModel, tag="source"):
    address: str = attr(name="address")
    port: int = attr(name="port", ge=0, le=65535)
    local: UdpLocal | None = element(tag="local", default=None)


class UdpInterface(_InterfaceBase, tag="interface"):
    type: Literal["udp"] = attr(name="type")
    source: UdpSource | None = element(tag="source", default=None)


class HostdevVendor(LibvirtXmlModel, tag="vendor"):
    id: HexNumber = attr(name="id")


class HostdevProduct(LibvirtXmlModel, tag="product"):
    id: HexNumber = attr(name="id")


class HostdevSourceAddress(LibvirtXmlModel, tag="address"):
    """``<address>`` of a hostdev interface: a PCI or USB host device."""

    type: Literal["pci", "usb"] | None = attr(name="type", default=None)
    domain: HexNumber | None = attr(name="domain", default=None)
    bus: HexNumber | None = attr(name="bus", default=None)
    slot: HexNumber | None = attr(name="slot", default=None)
    function: HexNumber | None = attr(name="function", default=None)
    multifunction: OnOff | None = attr(name="multifunction", default=None)
    device: HexNumber | None = attr(name="device", default=None)
    port: str | None = attr(name="port", default=None)


class HostdevSource(LibvirtXmlModel, tag="source"):
    missing: YesNo | None = attr(name="missing", default=None)
    vendor: HostdevVendor | None = element(tag="vendor", default=None)
    product: HostdevProduct | None = element(tag="product", default=None)
    address: HostdevSourceAddress | None = element(tag="address", default=None)


class HostdevInterface(_InterfaceBase, tag="interface"):
    type: Literal["hostdev"] = attr(name="type")
    source: HostdevSource | None = element(tag="source", default=None)


class VdpaSource(LibvirtXmlModel, tag="source"):
    dev: str = attr(name="dev")


class VdpaInterface(_InterfaceBase, tag="interface"):
    type: Literal["vdpa"] = attr(name="type")
    source: VdpaSource | None = element(tag="source", default=None)


class NullInterface(_InterfaceBase, tag="interface"):
    type: Literal["null"] = attr(name="type")


class VdsSource(LibvirtXmlModel, tag="source"):
    switchid: Uuid = attr(name="switchid")
    portid: int | None = attr(name="portid", default=None)
    portgroupid: str | None = attr(name="portgroupid", default=None)
    connectionid: int | None = attr(name="connectionid", default=None)


class VdsInterface(_InterfaceBase, tag="interface"):
    type: Literal["vds"] = attr(name="type")
    source: VdsSource | None = element(tag="source", default=None)


Interface = (
    BridgeInterface
    | NetworkInterface
    | EthernetInterface
    | VhostUserInterface
    | DirectInterface
    | UserInterface
    | InternalInterface
    | McastInterface
    | ClientInterface
    | ServerInterface
    | UdpInterface
    | HostdevInterface
    | VdpaInterface
    | NullInterface
    | VdsInterface
)
"""Any ``<interface>``; the variant is chosen by its ``type`` attribute."""
