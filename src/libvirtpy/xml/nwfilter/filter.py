"""``<filter>``: a network filter, a set of rules and references to other filters.

See https://libvirt.org/formatnwfilter.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.network import FilterRef
from libvirtpy.xml._types import Uuid
from libvirtpy.xml.nwfilter.rules import (
    AhIpv6Rule,
    AhRule,
    AllIpv6Rule,
    AllRule,
    ArpRule,
    EspIpv6Rule,
    EspRule,
    IcmpRule,
    Icmpv6Rule,
    IgmpRule,
    IpRule,
    Ipv6Rule,
    MacRule,
    RarpRule,
    SctpIpv6Rule,
    SctpRule,
    StpRule,
    TcpIpv6Rule,
    TcpRule,
    UdpIpv6Rule,
    UdpliteIpv6Rule,
    UdpliteRule,
    UdpRule,
    VlanRule,
)

__all__ = ["Filter", "FilterRule"]


class FilterRule(LibvirtXmlModel, tag="rule"):
    """``<rule>``: what to do with traffic that matches its protocol element.

    A rule has one protocol child (``tcp``, ``arp``, ...), so exactly one of the
    protocol fields is set.
    """

    action: Literal["drop", "accept", "reject", "continue", "return"] = attr(
        name="action"
    )
    direction: Literal["in", "out", "inout"] = attr(name="direction")
    priority: int | None = attr(name="priority", default=None)
    statematch: str | None = attr(name="statematch", default=None)
    ah: AhRule | None = element(tag="ah", default=None)
    ah_ipv6: AhIpv6Rule | None = element(tag="ah-ipv6", default=None)
    all: AllRule | None = element(tag="all", default=None)
    all_ipv6: AllIpv6Rule | None = element(tag="all-ipv6", default=None)
    arp: ArpRule | None = element(tag="arp", default=None)
    esp: EspRule | None = element(tag="esp", default=None)
    esp_ipv6: EspIpv6Rule | None = element(tag="esp-ipv6", default=None)
    icmp: IcmpRule | None = element(tag="icmp", default=None)
    icmpv6: Icmpv6Rule | None = element(tag="icmpv6", default=None)
    igmp: IgmpRule | None = element(tag="igmp", default=None)
    ip: IpRule | None = element(tag="ip", default=None)
    ipv6: Ipv6Rule | None = element(tag="ipv6", default=None)
    mac: MacRule | None = element(tag="mac", default=None)
    rarp: RarpRule | None = element(tag="rarp", default=None)
    sctp: SctpRule | None = element(tag="sctp", default=None)
    sctp_ipv6: SctpIpv6Rule | None = element(tag="sctp-ipv6", default=None)
    stp: StpRule | None = element(tag="stp", default=None)
    tcp: TcpRule | None = element(tag="tcp", default=None)
    tcp_ipv6: TcpIpv6Rule | None = element(tag="tcp-ipv6", default=None)
    udp: UdpRule | None = element(tag="udp", default=None)
    udp_ipv6: UdpIpv6Rule | None = element(tag="udp-ipv6", default=None)
    udplite: UdpliteRule | None = element(tag="udplite", default=None)
    udplite_ipv6: UdpliteIpv6Rule | None = element(tag="udplite-ipv6", default=None)
    vlan: VlanRule | None = element(tag="vlan", default=None)


class Filter(LibvirtXmlModel, tag="filter"):
    """``<filter>``: a named network filter."""

    name: str = attr(name="name")
    chain: str | None = attr(
        name="chain", default=None, description="``root`` for a top level filter."
    )
    priority: int | None = attr(name="priority", default=None)
    uuid: Uuid | None = element(tag="uuid", default=None)
    filterrefs: list[FilterRef] = element(tag="filterref", default_factory=list)
    rules: list[FilterRule] = element(tag="rule", default_factory=list)
