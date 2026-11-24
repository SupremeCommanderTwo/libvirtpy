"""``<networkport>``: a port of a virtual network.

See https://libvirt.org/formatnetworkport.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.network import Bandwidth, VirtualPort, Vlan
from libvirtpy.xml._shared.storage import HostPciAddress
from libvirtpy.xml._types import Uuid, YesNo

__all__ = [
    "NetworkPort",
    "PortMac",
    "PortOptions",
    "PortOwner",
    "PortPlug",
    "PortPlugDriver",
    "PortRxFilters",
]


class PortOwner(LibvirtXmlModel, tag="owner"):
    """``<owner>``: the domain that uses the port."""

    name: str = element(tag="name")
    uuid: Uuid = element(tag="uuid")


class PortMac(LibvirtXmlModel, tag="mac"):
    address: str = attr(name="address")


class PortRxFilters(LibvirtXmlModel, tag="rxfilters"):
    trust_guest: YesNo = attr(name="trustGuest")


class PortOptions(LibvirtXmlModel, tag="port"):
    isolated: YesNo | None = attr(name="isolated", default=None)


class PortPlugDriver(LibvirtXmlModel, tag="driver"):
    name: Literal["kvm", "vfio", "xen"] | None = attr(name="name", default=None)
    model: str | None = attr(name="model", default=None)
    iommufd: YesNo | None = attr(name="iommufd", default=None)


class PortPlug(LibvirtXmlModel, tag="plug"):
    r"""``<plug>``: how the port is connected to the host.

    One model for all ``type``\ s (``network``, ``bridge``, ``direct``,
    ``hostdev-pci``): they use a few different optional fields of one element.
    """

    type: Literal["network", "bridge", "direct", "hostdev-pci"] = attr(name="type")
    bridge: str | None = attr(name="bridge", default=None)
    mac_table_manager: Literal["kernel", "libvirt"] | None = attr(
        name="macTableManager", default=None
    )
    dev: str | None = attr(name="dev", default=None)
    mode: Literal["bridge", "passthrough", "private", "vepa"] | None = attr(
        name="mode", default=None
    )
    managed: YesNo | None = attr(name="managed", default=None)
    driver: PortPlugDriver | None = element(tag="driver", default=None)
    address: HostPciAddress | None = element(tag="address", default=None)


class NetworkPort(LibvirtXmlModel, tag="networkport"):
    """``<networkport>``: a port of a virtual network."""

    uuid: Uuid = element(tag="uuid")
    owner: PortOwner = element(tag="owner")
    mac: PortMac = element(tag="mac")
    group: str | None = element(tag="group", default=None)
    rxfilters: PortRxFilters | None = element(tag="rxfilters", default=None)
    virtualport: VirtualPort | None = element(tag="virtualport", default=None)
    bandwidth: Bandwidth | None = element(tag="bandwidth", default=None)
    vlan: Vlan | None = element(tag="vlan", default=None)
    port: PortOptions | None = element(tag="port", default=None)
    plug: PortPlug | None = element(tag="plug", default=None)
