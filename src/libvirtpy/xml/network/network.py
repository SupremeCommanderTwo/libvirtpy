"""``<network>``: a virtual network.

See https://libvirt.org/formatnetwork.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.metadata import Metadata
from libvirtpy.xml._shared.network import Bandwidth, Route, VirtualPort, Vlan
from libvirtpy.xml._types import HexNumber, OnOff, Uuid, YesNo

__all__ = [
    "DNSMASQ_NAMESPACE",
    "DhcpBootp",
    "DhcpHost",
    "DhcpLease",
    "DhcpRange",
    "Network",
    "NetworkBridge",
    "NetworkDhcp",
    "NetworkDns",
    "NetworkDnsDomain",
    "NetworkDnsForwarder",
    "NetworkDnsHost",
    "NetworkDnsSrv",
    "NetworkDnsTxt",
    "NetworkForward",
    "NetworkForwardAddress",
    "NetworkForwardDriver",
    "NetworkForwardInterface",
    "NetworkForwardNat",
    "NetworkIp",
    "NetworkMac",
    "NetworkMtu",
    "NetworkPortOptions",
    "NetworkTftp",
    "Portgroup",
]

DNSMASQ_NAMESPACE = "http://libvirt.org/schemas/network/dnsmasq/1.0"


class NetworkBridge(LibvirtXmlModel, tag="bridge"):
    """``<bridge>``: the host bridge device."""

    name: str | None = attr(name="name", default=None)
    zone: str | None = attr(name="zone", default=None, description="Firewall zone.")
    stp: OnOff | None = attr(name="stp", default=None)
    delay: int | None = attr(name="delay", default=None, ge=0)
    mac_table_manager: Literal["kernel", "libvirt"] | None = attr(
        name="macTableManager", default=None
    )


class NetworkMtu(LibvirtXmlModel, tag="mtu"):
    size: int = attr(name="size", ge=0, le=65535)


class NetworkMac(LibvirtXmlModel, tag="mac"):
    address: str = attr(name="address")


class NetworkForwardInterface(LibvirtXmlModel, tag="interface"):
    """``<interface>`` in ``<forward>``: a host interface of the pool."""

    dev: str = attr(name="dev")
    connections: int | None = attr(name="connections", default=None, ge=0)


class NetworkForwardAddress(LibvirtXmlModel, tag="address"):
    """``<address>`` in ``<forward>``: a PCI device of the pool."""

    type: Literal["pci"] = attr(name="type")
    domain: HexNumber | None = attr(name="domain", default=None)
    bus: HexNumber | None = attr(name="bus", default=None)
    slot: HexNumber | None = attr(name="slot", default=None)
    function: HexNumber | None = attr(name="function", default=None)
    multifunction: OnOff | None = attr(name="multifunction", default=None)
    connections: int | None = attr(name="connections", default=None, ge=0)


class ForwardPf(LibvirtXmlModel, tag="pf"):
    dev: str = attr(name="dev")


class NetworkForwardDriver(LibvirtXmlModel, tag="driver"):
    """``<driver>`` of a hostdev network."""

    name: Literal["kvm", "vfio", "xen"] | None = attr(name="name", default=None)
    model: str | None = attr(name="model", default=None)
    iommufd: YesNo | None = attr(name="iommufd", default=None)


class NatAddress(LibvirtXmlModel, tag="address"):
    start: str = attr(name="start")
    end: str = attr(name="end")


class NatPort(LibvirtXmlModel, tag="port"):
    start: int = attr(name="start", ge=0, le=65535)
    end: int = attr(name="end", ge=0, le=65535)


class NetworkForwardNat(LibvirtXmlModel, tag="nat"):
    """``<nat>``: the address and port range used for NAT."""

    ipv6: YesNo | None = attr(name="ipv6", default=None)
    address: NatAddress | None = element(tag="address", default=None)
    port: NatPort | None = element(tag="port", default=None)


class NetworkForward(LibvirtXmlModel, tag="forward"):
    """``<forward>``: how the network is connected to the outside."""

    dev: str | None = attr(name="dev", default=None)
    mode: (
        Literal[
            "nat",
            "route",
            "open",
            "bridge",
            "passthrough",
            "private",
            "vepa",
            "hostdev",
        ]
        | None
    ) = attr(name="mode", default=None)
    managed: YesNo | None = attr(name="managed", default=None)
    interfaces: list[NetworkForwardInterface] = element(
        tag="interface", default_factory=list
    )
    addresses: list[NetworkForwardAddress] = element(
        tag="address", default_factory=list
    )
    pf: ForwardPf | None = element(tag="pf", default=None)
    driver: NetworkForwardDriver | None = element(tag="driver", default=None)
    nat: NetworkForwardNat | None = element(tag="nat", default=None)


class Portgroup(LibvirtXmlModel, tag="portgroup"):
    """``<portgroup>``: a named set of port settings."""

    name: str = attr(name="name")
    default: YesNo | None = attr(name="default", default=None)
    trust_guest_rx_filters: YesNo | None = attr(
        name="trustGuestRxFilters", default=None
    )
    virtualport: VirtualPort | None = element(tag="virtualport", default=None)
    bandwidth: Bandwidth | None = element(tag="bandwidth", default=None)
    vlan: Vlan | None = element(tag="vlan", default=None)


class NetworkDnsDomain(LibvirtXmlModel, tag="domain"):
    """``<domain>``: the DNS domain of the network."""

    name: str = attr(name="name")
    local_only: YesNo | None = attr(name="localOnly", default=None)
    registered: YesNo | None = attr(name="register", default=None)


class NetworkDnsForwarder(LibvirtXmlModel, tag="forwarder"):
    addr: str | None = attr(name="addr", default=None)
    domain: str | None = attr(name="domain", default=None)
    port: int | None = attr(name="port", default=None, ge=0, le=65535)


class NetworkDnsTxt(LibvirtXmlModel, tag="txt"):
    name: str = attr(name="name")
    value: str = attr(name="value")


class NetworkDnsSrv(LibvirtXmlModel, tag="srv"):
    service: str = attr(name="service")
    protocol: str = attr(name="protocol")
    domain: str | None = attr(name="domain", default=None)
    target: str | None = attr(name="target", default=None)
    port: int | None = attr(name="port", default=None, ge=0, le=65535)
    priority: int | None = attr(name="priority", default=None, ge=0, le=65535)
    weight: int | None = attr(name="weight", default=None, ge=0, le=65535)


class NetworkDnsHost(LibvirtXmlModel, tag="host"):
    ip: str = attr(name="ip")
    hostnames: list[str] = element(tag="hostname", default_factory=list)


class NetworkDns(LibvirtXmlModel, tag="dns"):
    """``<dns>``: the DNS server of the network."""

    enable: YesNo | None = attr(name="enable", default=None)
    forward_plain_names: YesNo | None = attr(name="forwardPlainNames", default=None)
    forwarders: list[NetworkDnsForwarder] = element(
        tag="forwarder", default_factory=list
    )
    txts: list[NetworkDnsTxt] = element(tag="txt", default_factory=list)
    srvs: list[NetworkDnsSrv] = element(tag="srv", default_factory=list)
    hosts: list[NetworkDnsHost] = element(tag="host", default_factory=list)


class NetworkPortOptions(LibvirtXmlModel, tag="port"):
    """``<port>``: port options of the network's switch."""

    isolated: YesNo | None = attr(name="isolated", default=None)


class NetworkTftp(LibvirtXmlModel, tag="tftp"):
    root: str = attr(name="root")


class DhcpLease(LibvirtXmlModel, tag="lease"):
    """``<lease>``: how long leases last."""

    expiry: int = attr(name="expiry", ge=0)
    unit: Literal["seconds", "minutes", "hours"] | None = attr(
        name="unit", default=None
    )


class DhcpRange(LibvirtXmlModel, tag="range"):
    start: str = attr(name="start")
    end: str = attr(name="end")
    lease: DhcpLease | None = element(tag="lease", default=None)


class DhcpHost(LibvirtXmlModel, tag="host"):
    """``<host>``: a static DHCP lease."""

    mac: str | None = attr(name="mac", default=None)
    id: str | None = attr(name="id", default=None, description="DUID, for DHCPv6.")
    name: str | None = attr(name="name", default=None)
    ip: str = attr(name="ip")
    lease: DhcpLease | None = element(tag="lease", default=None)


class DhcpBootp(LibvirtXmlModel, tag="bootp"):
    file: str = attr(name="file")
    server: str | None = attr(name="server", default=None)


class NetworkDhcp(LibvirtXmlModel, tag="dhcp"):
    """``<dhcp>``: the DHCP server of an IP range."""

    ranges: list[DhcpRange] = element(tag="range", default_factory=list)
    hosts: list[DhcpHost] = element(tag="host", default_factory=list)
    bootp: DhcpBootp | None = element(tag="bootp", default=None)


class NetworkIp(LibvirtXmlModel, tag="ip"):
    """``<ip>``: an address of the host bridge, with its DHCP and TFTP services."""

    address: str | None = attr(name="address", default=None)
    netmask: str | None = attr(name="netmask", default=None)
    prefix: int | None = attr(name="prefix", default=None, ge=0)
    family: Literal["ipv4", "ipv6"] | None = attr(name="family", default=None)
    local_ptr: YesNo | None = attr(name="localPtr", default=None)
    tftp: NetworkTftp | None = element(tag="tftp", default=None)
    dhcp: NetworkDhcp | None = element(tag="dhcp", default=None)


class DnsmasqOption(
    LibvirtXmlModel, tag="option", ns="dnsmasq", nsmap={"dnsmasq": DNSMASQ_NAMESPACE}
):
    """``<dnsmasq:option>``: a raw dnsmasq configuration line."""

    value: str = attr(name="value")


class DnsmasqOptions(
    LibvirtXmlModel, tag="options", ns="dnsmasq", nsmap={"dnsmasq": DNSMASQ_NAMESPACE}
):
    """``<dnsmasq:options>``: extra dnsmasq settings."""

    options: list[DnsmasqOption] = element(tag="option", default_factory=list)


class Network(LibvirtXmlModel, tag="network"):
    """``<network>``: a virtual network."""

    connections: int | None = attr(name="connections", default=None, ge=0)
    ipv6: YesNo | None = attr(name="ipv6", default=None)
    trust_guest_rx_filters: YesNo | None = attr(
        name="trustGuestRxFilters", default=None
    )
    name: str = element(tag="name")
    uuid: Uuid | None = element(tag="uuid", default=None)
    title: str | None = element(tag="title", default=None)
    description: str | None = element(tag="description", default=None)
    metadata: Metadata | None = element(tag="metadata", default=None)
    bridge: NetworkBridge | None = element(tag="bridge", default=None)
    mtu: NetworkMtu | None = element(tag="mtu", default=None)
    mac: NetworkMac | None = element(tag="mac", default=None)
    forward: NetworkForward | None = element(tag="forward", default=None)
    virtualport: VirtualPort | None = element(tag="virtualport", default=None)
    portgroups: list[Portgroup] = element(tag="portgroup", default_factory=list)
    domain: NetworkDnsDomain | None = element(tag="domain", default=None)
    dns: NetworkDns | None = element(tag="dns", default=None)
    bandwidth: Bandwidth | None = element(tag="bandwidth", default=None)
    vlan: Vlan | None = element(tag="vlan", default=None)
    port: NetworkPortOptions | None = element(tag="port", default=None)
    ips: list[NetworkIp] = element(tag="ip", default_factory=list)
    routes: list[Route] = element(tag="route", default_factory=list)
    dnsmasq_options: DnsmasqOptions | None = element(
        tag="options",
        ns="dnsmasq",
        nsmap={"dnsmasq": DNSMASQ_NAMESPACE},
        default=None,
    )
