"""Network settings shared by ``<interface>`` and ``<network>``.

``domain`` and ``network`` must not import each other, so the structures that
both use live here and each package re-exports them.
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import Uuid

__all__ = [
    "Bandwidth",
    "BandwidthLimit",
    "FilterParameter",
    "FilterRef",
    "Inbound",
    "Outbound",
    "Route",
    "VirtualPort",
    "VirtualPortParameters",
    "Vlan",
    "VlanTag",
]


class VirtualPortParameters(LibvirtXmlModel, tag="parameters"):
    """``<parameters>`` of a virtual port; which are valid depends on its type."""

    managerid: int | None = attr(name="managerid", default=None, ge=0)
    typeid: int | None = attr(name="typeid", default=None, ge=0)
    typeidversion: int | None = attr(name="typeidversion", default=None, ge=0)
    instanceid: Uuid | None = attr(name="instanceid", default=None)
    profileid: str | None = attr(name="profileid", default=None)
    interfaceid: Uuid | None = attr(name="interfaceid", default=None)


class VirtualPort(LibvirtXmlModel, tag="virtualport"):
    """``<virtualport>``: 802.1Qbg, 802.1Qbh, Open vSwitch or MidoNet settings."""

    type: Literal["802.1Qbg", "802.1Qbh", "openvswitch", "midonet"] | None = attr(
        name="type", default=None
    )
    parameters: VirtualPortParameters | None = element(tag="parameters", default=None)


class BandwidthLimit(LibvirtXmlModel):
    """Base of ``<inbound>`` and ``<outbound>``; rates in KiB/s, burst in KiB."""

    average: int | None = attr(name="average", default=None, ge=0)
    peak: int | None = attr(name="peak", default=None, ge=0)
    floor: int | None = attr(name="floor", default=None, ge=0)
    burst: int | None = attr(name="burst", default=None, ge=0)


class Inbound(BandwidthLimit, tag="inbound"):
    """``<inbound>``: limits of incoming traffic."""


class Outbound(BandwidthLimit, tag="outbound"):
    """``<outbound>``: limits of outgoing traffic."""


class Bandwidth(LibvirtXmlModel, tag="bandwidth"):
    """``<bandwidth>``: traffic shaping."""

    class_id: int | None = attr(name="classID", default=None, ge=1)
    inbound: Inbound | None = element(tag="inbound", default=None)
    outbound: Outbound | None = element(tag="outbound", default=None)


class VlanTag(LibvirtXmlModel, tag="tag"):
    id: int = attr(name="id", ge=0)
    native_mode: Literal["tagged", "untagged"] | None = attr(
        name="nativeMode", default=None
    )


class Vlan(LibvirtXmlModel, tag="vlan"):
    """``<vlan>``: VLAN tags."""

    trunk: Literal["yes"] | None = attr(name="trunk", default=None)
    tags: list[VlanTag] = element(tag="tag", default_factory=list)


class Route(LibvirtXmlModel, tag="route"):
    """``<route>``: a route (of a guest interface or of a network)."""

    family: str | None = attr(name="family", default=None)
    address: str | None = attr(name="address", default=None)
    netmask: str | None = attr(name="netmask", default=None)
    prefix: int | None = attr(name="prefix", default=None, ge=0)
    gateway: str = attr(name="gateway")
    metric: int | None = attr(name="metric", default=None, ge=0)


class FilterParameter(LibvirtXmlModel, tag="parameter"):
    name: str = attr(name="name")
    value: str = attr(name="value")


class FilterRef(LibvirtXmlModel, tag="filterref"):
    """``<filterref>``: a network filter and its parameters."""

    filter: str = attr(name="filter")
    parameters: list[FilterParameter] = element(tag="parameter", default_factory=list)
