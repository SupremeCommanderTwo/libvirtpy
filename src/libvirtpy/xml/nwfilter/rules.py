"""``<rule>`` of a network filter: one class per protocol element.

Every attribute of a rule element is text in the schema (addresses, ports and
ranges, ``0x`` numbers, ``yes``/``no`` for ``match``), so they are kept as
strings, exactly as written. The classes were written from libvirt's
``nwfilter.rng``; ``tools/schema_coverage.py`` checks them against it.

See https://libvirt.org/formatnwfilter.html#filtering-rules
"""

from pydantic_xml import attr

from libvirtpy.xml._base import LibvirtXmlModel

__all__ = [
    "AhIpv6Rule",
    "AhRule",
    "AllIpv6Rule",
    "AllRule",
    "ArpRule",
    "EspIpv6Rule",
    "EspRule",
    "IcmpRule",
    "Icmpv6Rule",
    "IgmpRule",
    "IpRule",
    "Ipv6Rule",
    "MacRule",
    "RarpRule",
    "SctpIpv6Rule",
    "SctpRule",
    "StpRule",
    "TcpIpv6Rule",
    "TcpRule",
    "UdpIpv6Rule",
    "UdpRule",
    "UdpliteIpv6Rule",
    "UdpliteRule",
    "VlanRule",
]


class AhRule(LibvirtXmlModel, tag="ah"):
    """``<ah>``: match on AH traffic."""

    comment: str | None = attr(name="comment", default=None)
    connlimit_above: str | None = attr(name="connlimit-above", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    ipset: str | None = attr(name="ipset", default=None)
    ipsetflags: str | None = attr(name="ipsetflags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    state: str | None = attr(name="state", default=None)


class AhIpv6Rule(LibvirtXmlModel, tag="ah-ipv6"):
    """``<ah-ipv6>``: match on AH-IPV6 traffic."""

    comment: str | None = attr(name="comment", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)


class AllRule(LibvirtXmlModel, tag="all"):
    """``<all>``: match on ALL traffic."""

    comment: str | None = attr(name="comment", default=None)
    connlimit_above: str | None = attr(name="connlimit-above", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    ipset: str | None = attr(name="ipset", default=None)
    ipsetflags: str | None = attr(name="ipsetflags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    state: str | None = attr(name="state", default=None)


class AllIpv6Rule(LibvirtXmlModel, tag="all-ipv6"):
    """``<all-ipv6>``: match on ALL-IPV6 traffic."""

    comment: str | None = attr(name="comment", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)


class ArpRule(LibvirtXmlModel, tag="arp"):
    """``<arp>``: match on ARP traffic."""

    arpdstipaddr: str | None = attr(name="arpdstipaddr", default=None)
    arpdstmacaddr: str | None = attr(name="arpdstmacaddr", default=None)
    arpsrcipaddr: str | None = attr(name="arpsrcipaddr", default=None)
    arpsrcmacaddr: str | None = attr(name="arpsrcmacaddr", default=None)
    comment: str | None = attr(name="comment", default=None)
    dstmacaddr: str | None = attr(name="dstmacaddr", default=None)
    dstmacmask: str | None = attr(name="dstmacmask", default=None)
    gratuitous: str | None = attr(name="gratuitous", default=None)
    hwtype: str | None = attr(name="hwtype", default=None)
    match: str | None = attr(name="match", default=None)
    opcode: str | None = attr(name="opcode", default=None)
    protocoltype: str | None = attr(name="protocoltype", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcmacmask: str | None = attr(name="srcmacmask", default=None)


class EspRule(LibvirtXmlModel, tag="esp"):
    """``<esp>``: match on ESP traffic."""

    comment: str | None = attr(name="comment", default=None)
    connlimit_above: str | None = attr(name="connlimit-above", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    ipset: str | None = attr(name="ipset", default=None)
    ipsetflags: str | None = attr(name="ipsetflags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    state: str | None = attr(name="state", default=None)


class EspIpv6Rule(LibvirtXmlModel, tag="esp-ipv6"):
    """``<esp-ipv6>``: match on ESP-IPV6 traffic."""

    comment: str | None = attr(name="comment", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)


class IcmpRule(LibvirtXmlModel, tag="icmp"):
    """``<icmp>``: match on ICMP traffic."""

    code: str | None = attr(name="code", default=None)
    comment: str | None = attr(name="comment", default=None)
    connlimit_above: str | None = attr(name="connlimit-above", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    ipset: str | None = attr(name="ipset", default=None)
    ipsetflags: str | None = attr(name="ipsetflags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    state: str | None = attr(name="state", default=None)
    type: str | None = attr(name="type", default=None)


class Icmpv6Rule(LibvirtXmlModel, tag="icmpv6"):
    """``<icmpv6>``: match on ICMPV6 traffic."""

    code: str | None = attr(name="code", default=None)
    comment: str | None = attr(name="comment", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    type: str | None = attr(name="type", default=None)


class IgmpRule(LibvirtXmlModel, tag="igmp"):
    """``<igmp>``: match on IGMP traffic."""

    comment: str | None = attr(name="comment", default=None)
    connlimit_above: str | None = attr(name="connlimit-above", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    ipset: str | None = attr(name="ipset", default=None)
    ipsetflags: str | None = attr(name="ipsetflags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    state: str | None = attr(name="state", default=None)


class IpRule(LibvirtXmlModel, tag="ip"):
    """``<ip>``: match on IP traffic."""

    comment: str | None = attr(name="comment", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstmacaddr: str | None = attr(name="dstmacaddr", default=None)
    dstmacmask: str | None = attr(name="dstmacmask", default=None)
    dstportend: str | None = attr(name="dstportend", default=None)
    dstportstart: str | None = attr(name="dstportstart", default=None)
    match: str | None = attr(name="match", default=None)
    protocol: str | None = attr(name="protocol", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcmacmask: str | None = attr(name="srcmacmask", default=None)
    srcportend: str | None = attr(name="srcportend", default=None)
    srcportstart: str | None = attr(name="srcportstart", default=None)


class Ipv6Rule(LibvirtXmlModel, tag="ipv6"):
    """``<ipv6>``: match on IPV6 traffic."""

    code: str | None = attr(name="code", default=None)
    codeend: str | None = attr(name="codeend", default=None)
    comment: str | None = attr(name="comment", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstmacaddr: str | None = attr(name="dstmacaddr", default=None)
    dstmacmask: str | None = attr(name="dstmacmask", default=None)
    dstportend: str | None = attr(name="dstportend", default=None)
    dstportstart: str | None = attr(name="dstportstart", default=None)
    match: str | None = attr(name="match", default=None)
    protocol: str | None = attr(name="protocol", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcmacmask: str | None = attr(name="srcmacmask", default=None)
    srcportend: str | None = attr(name="srcportend", default=None)
    srcportstart: str | None = attr(name="srcportstart", default=None)
    type: str | None = attr(name="type", default=None)
    typeend: str | None = attr(name="typeend", default=None)


class MacRule(LibvirtXmlModel, tag="mac"):
    """``<mac>``: match on MAC traffic."""

    comment: str | None = attr(name="comment", default=None)
    dstmacaddr: str | None = attr(name="dstmacaddr", default=None)
    dstmacmask: str | None = attr(name="dstmacmask", default=None)
    match: str | None = attr(name="match", default=None)
    protocolid: str | None = attr(name="protocolid", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcmacmask: str | None = attr(name="srcmacmask", default=None)


class RarpRule(LibvirtXmlModel, tag="rarp"):
    """``<rarp>``: match on RARP traffic."""

    arpdstipaddr: str | None = attr(name="arpdstipaddr", default=None)
    arpdstmacaddr: str | None = attr(name="arpdstmacaddr", default=None)
    arpsrcipaddr: str | None = attr(name="arpsrcipaddr", default=None)
    arpsrcmacaddr: str | None = attr(name="arpsrcmacaddr", default=None)
    comment: str | None = attr(name="comment", default=None)
    dstmacaddr: str | None = attr(name="dstmacaddr", default=None)
    dstmacmask: str | None = attr(name="dstmacmask", default=None)
    gratuitous: str | None = attr(name="gratuitous", default=None)
    hwtype: str | None = attr(name="hwtype", default=None)
    match: str | None = attr(name="match", default=None)
    opcode: str | None = attr(name="opcode", default=None)
    protocoltype: str | None = attr(name="protocoltype", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcmacmask: str | None = attr(name="srcmacmask", default=None)


class SctpRule(LibvirtXmlModel, tag="sctp"):
    """``<sctp>``: match on SCTP traffic."""

    comment: str | None = attr(name="comment", default=None)
    connlimit_above: str | None = attr(name="connlimit-above", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    dstportend: str | None = attr(name="dstportend", default=None)
    dstportstart: str | None = attr(name="dstportstart", default=None)
    ipset: str | None = attr(name="ipset", default=None)
    ipsetflags: str | None = attr(name="ipsetflags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcportend: str | None = attr(name="srcportend", default=None)
    srcportstart: str | None = attr(name="srcportstart", default=None)
    state: str | None = attr(name="state", default=None)


class SctpIpv6Rule(LibvirtXmlModel, tag="sctp-ipv6"):
    """``<sctp-ipv6>``: match on SCTP-IPV6 traffic."""

    comment: str | None = attr(name="comment", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    dstportend: str | None = attr(name="dstportend", default=None)
    dstportstart: str | None = attr(name="dstportstart", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcportend: str | None = attr(name="srcportend", default=None)
    srcportstart: str | None = attr(name="srcportstart", default=None)


class StpRule(LibvirtXmlModel, tag="stp"):
    """``<stp>``: match on STP traffic."""

    age: str | None = attr(name="age", default=None)
    age_hi: str | None = attr(name="age-hi", default=None)
    comment: str | None = attr(name="comment", default=None)
    flags: str | None = attr(name="flags", default=None)
    forward_delay: str | None = attr(name="forward-delay", default=None)
    forward_delay_hi: str | None = attr(name="forward-delay-hi", default=None)
    hello_time: str | None = attr(name="hello-time", default=None)
    hello_time_hi: str | None = attr(name="hello-time-hi", default=None)
    match: str | None = attr(name="match", default=None)
    max_age: str | None = attr(name="max-age", default=None)
    max_age_hi: str | None = attr(name="max-age-hi", default=None)
    port: str | None = attr(name="port", default=None)
    port_hi: str | None = attr(name="port-hi", default=None)
    root_address: str | None = attr(name="root-address", default=None)
    root_address_mask: str | None = attr(name="root-address-mask", default=None)
    root_cost: str | None = attr(name="root-cost", default=None)
    root_cost_hi: str | None = attr(name="root-cost-hi", default=None)
    root_priority: str | None = attr(name="root-priority", default=None)
    root_priority_hi: str | None = attr(name="root-priority-hi", default=None)
    sender_address: str | None = attr(name="sender-address", default=None)
    sender_address_mask: str | None = attr(name="sender-address-mask", default=None)
    sender_priority: str | None = attr(name="sender-priority", default=None)
    sender_priority_hi: str | None = attr(name="sender-priority-hi", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcmacmask: str | None = attr(name="srcmacmask", default=None)
    type: str | None = attr(name="type", default=None)


class TcpRule(LibvirtXmlModel, tag="tcp"):
    """``<tcp>``: match on TCP traffic."""

    comment: str | None = attr(name="comment", default=None)
    connlimit_above: str | None = attr(name="connlimit-above", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    dstportend: str | None = attr(name="dstportend", default=None)
    dstportstart: str | None = attr(name="dstportstart", default=None)
    flags: str | None = attr(name="flags", default=None)
    ipset: str | None = attr(name="ipset", default=None)
    ipsetflags: str | None = attr(name="ipsetflags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcportend: str | None = attr(name="srcportend", default=None)
    srcportstart: str | None = attr(name="srcportstart", default=None)
    state: str | None = attr(name="state", default=None)


class TcpIpv6Rule(LibvirtXmlModel, tag="tcp-ipv6"):
    """``<tcp-ipv6>``: match on TCP-IPV6 traffic."""

    comment: str | None = attr(name="comment", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    dstportend: str | None = attr(name="dstportend", default=None)
    dstportstart: str | None = attr(name="dstportstart", default=None)
    flags: str | None = attr(name="flags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcportend: str | None = attr(name="srcportend", default=None)
    srcportstart: str | None = attr(name="srcportstart", default=None)


class UdpRule(LibvirtXmlModel, tag="udp"):
    """``<udp>``: match on UDP traffic."""

    comment: str | None = attr(name="comment", default=None)
    connlimit_above: str | None = attr(name="connlimit-above", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    dstportend: str | None = attr(name="dstportend", default=None)
    dstportstart: str | None = attr(name="dstportstart", default=None)
    ipset: str | None = attr(name="ipset", default=None)
    ipsetflags: str | None = attr(name="ipsetflags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcportend: str | None = attr(name="srcportend", default=None)
    srcportstart: str | None = attr(name="srcportstart", default=None)
    state: str | None = attr(name="state", default=None)


class UdpIpv6Rule(LibvirtXmlModel, tag="udp-ipv6"):
    """``<udp-ipv6>``: match on UDP-IPV6 traffic."""

    comment: str | None = attr(name="comment", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    dstportend: str | None = attr(name="dstportend", default=None)
    dstportstart: str | None = attr(name="dstportstart", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcportend: str | None = attr(name="srcportend", default=None)
    srcportstart: str | None = attr(name="srcportstart", default=None)


class UdpliteRule(LibvirtXmlModel, tag="udplite"):
    """``<udplite>``: match on UDPLITE traffic."""

    comment: str | None = attr(name="comment", default=None)
    connlimit_above: str | None = attr(name="connlimit-above", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    ipset: str | None = attr(name="ipset", default=None)
    ipsetflags: str | None = attr(name="ipsetflags", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    state: str | None = attr(name="state", default=None)


class UdpliteIpv6Rule(LibvirtXmlModel, tag="udplite-ipv6"):
    """``<udplite-ipv6>``: match on UDPLITE-IPV6 traffic."""

    comment: str | None = attr(name="comment", default=None)
    dscp: str | None = attr(name="dscp", default=None)
    dstipaddr: str | None = attr(name="dstipaddr", default=None)
    dstipfrom: str | None = attr(name="dstipfrom", default=None)
    dstipmask: str | None = attr(name="dstipmask", default=None)
    dstipto: str | None = attr(name="dstipto", default=None)
    match: str | None = attr(name="match", default=None)
    srcipaddr: str | None = attr(name="srcipaddr", default=None)
    srcipfrom: str | None = attr(name="srcipfrom", default=None)
    srcipmask: str | None = attr(name="srcipmask", default=None)
    srcipto: str | None = attr(name="srcipto", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)


class VlanRule(LibvirtXmlModel, tag="vlan"):
    """``<vlan>``: match on VLAN traffic."""

    comment: str | None = attr(name="comment", default=None)
    dstmacaddr: str | None = attr(name="dstmacaddr", default=None)
    dstmacmask: str | None = attr(name="dstmacmask", default=None)
    encap_protocol: str | None = attr(name="encap-protocol", default=None)
    match: str | None = attr(name="match", default=None)
    srcmacaddr: str | None = attr(name="srcmacaddr", default=None)
    srcmacmask: str | None = attr(name="srcmacmask", default=None)
    vlanid: str | None = attr(name="vlanid", default=None)
