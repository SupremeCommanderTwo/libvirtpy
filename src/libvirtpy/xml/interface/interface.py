"""``<interface>`` as a host network interface (``virsh iface-*``).

Not to be confused with a domain's ``<interface>`` device
(``libvirtpy.xml.domain.devices.interface``).

One model covers the ``ethernet``, ``bridge``, ``bond`` and ``vlan`` types: a
bridge or bond holds other interfaces, which are the same element, so the
model refers to itself.

See https://libvirt.org/formatinterface.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff, PresenceFlag, YesNo

__all__ = [
    "HostInterface",
    "HostInterfaceBond",
    "HostInterfaceBridge",
    "HostInterfaceVlan",
    "InterfaceProtocol",
]


class InterfaceStart(LibvirtXmlModel, tag="start"):
    mode: Literal["onboot", "none", "hotplug"] = attr(name="mode")


class InterfaceMac(LibvirtXmlModel, tag="mac"):
    address: str = attr(name="address")


class InterfaceLink(LibvirtXmlModel, tag="link"):
    speed: int | None = attr(name="speed", default=None, ge=0)
    state: (
        Literal[
            "unknown",
            "notpresent",
            "down",
            "lowerlayerdown",
            "testing",
            "dormant",
            "up",
        ]
        | None
    ) = attr(name="state", default=None)


class InterfaceMtu(LibvirtXmlModel, tag="mtu"):
    size: int = attr(name="size", ge=0)


class ProtocolDhcp(LibvirtXmlModel, tag="dhcp"):
    peerdns: YesNo | None = attr(name="peerdns", default=None)


class ProtocolIp(LibvirtXmlModel, tag="ip"):
    address: str = attr(name="address")
    prefix: int | None = attr(name="prefix", default=None, ge=0)


class ProtocolRoute(LibvirtXmlModel, tag="route"):
    gateway: str = attr(name="gateway")


class InterfaceProtocol(LibvirtXmlModel, tag="protocol"):
    """``<protocol>``: the IPv4 or IPv6 configuration of the interface."""

    family: Literal["ipv4", "ipv6"] = attr(name="family")
    autoconf: PresenceFlag | None = element(tag="autoconf", default=None)
    dhcp: ProtocolDhcp | None = element(tag="dhcp", default=None)
    ips: list[ProtocolIp] = element(tag="ip", default_factory=list)
    route: ProtocolRoute | None = element(tag="route", default=None)


class HostInterfaceBridge(LibvirtXmlModel, tag="bridge"):
    """``<bridge>``: the ports of a bridge interface."""

    stp: OnOff | None = attr(name="stp", default=None)
    delay: str | None = attr(
        name="delay", default=None, description="Seconds, a decimal number as text."
    )
    interfaces: list[HostInterface] = element(tag="interface", default_factory=list)


class BondMiimon(LibvirtXmlModel, tag="miimon"):
    freq: int = attr(name="freq", ge=0)
    downdelay: int | None = attr(name="downdelay", default=None, ge=0)
    updelay: int | None = attr(name="updelay", default=None, ge=0)
    carrier: Literal["ioctl", "netif"] | None = attr(name="carrier", default=None)


class BondArpmon(LibvirtXmlModel, tag="arpmon"):
    interval: int = attr(name="interval", ge=0)
    target: str = attr(name="target")
    validate_: Literal["none", "active", "backup", "all"] | None = attr(
        name="validate", default=None
    )


class HostInterfaceBond(LibvirtXmlModel, tag="bond"):
    """``<bond>``: the slaves and link monitoring of a bond interface."""

    mode: (
        Literal[
            "balance-rr",
            "active-backup",
            "balance-xor",
            "broadcast",
            "802.3ad",
            "balance-tlb",
            "balance-alb",
        ]
        | None
    ) = attr(name="mode", default=None)
    miimon: BondMiimon | None = element(tag="miimon", default=None)
    arpmon: BondArpmon | None = element(tag="arpmon", default=None)
    interfaces: list[HostInterface] = element(tag="interface", default_factory=list)


class VlanDevice(LibvirtXmlModel, tag="interface"):
    name: str = attr(name="name")


class HostInterfaceVlan(LibvirtXmlModel, tag="vlan"):
    """``<vlan>``: the tag and parent device of a VLAN interface."""

    tag: int = attr(name="tag", ge=0, le=4095)
    interface: VlanDevice = element(tag="interface")


class HostInterface(LibvirtXmlModel, tag="interface"):
    """``<interface>``: a host network interface."""

    type: Literal["ethernet", "bridge", "bond", "vlan"] = attr(name="type")
    name: str | None = attr(name="name", default=None)
    start: InterfaceStart | None = element(tag="start", default=None)
    mac: InterfaceMac | None = element(tag="mac", default=None)
    link: InterfaceLink | None = element(tag="link", default=None)
    mtu: InterfaceMtu | None = element(tag="mtu", default=None)
    protocols: list[InterfaceProtocol] = element(tag="protocol", default_factory=list)
    bridge: HostInterfaceBridge | None = element(tag="bridge", default=None)
    bond: HostInterfaceBond | None = element(tag="bond", default=None)
    vlan: HostInterfaceVlan | None = element(tag="vlan", default=None)


# The bridge and the bond hold ``HostInterface``, which is defined after them.
HostInterfaceBridge.model_rebuild()
HostInterfaceBond.model_rebuild()
