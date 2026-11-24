"""``<filterbinding>``: a network filter applied to a port.

See https://libvirt.org/formatnwfilter.html#network-filter-bindings
"""

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.network import FilterRef
from libvirtpy.xml._types import Uuid

__all__ = [
    "FilterBinding",
    "FilterBindingBackend",
    "FilterBindingLinkdev",
    "FilterBindingMac",
    "FilterBindingOwner",
    "FilterBindingPortdev",
]


class FilterBindingOwner(LibvirtXmlModel, tag="owner"):
    name: str = element(tag="name")
    uuid: Uuid = element(tag="uuid")


class FilterBindingPortdev(LibvirtXmlModel, tag="portdev"):
    name: str = attr(name="name")


class FilterBindingLinkdev(LibvirtXmlModel, tag="linkdev"):
    name: str = attr(name="name")


class FilterBindingMac(LibvirtXmlModel, tag="mac"):
    address: str = attr(name="address")


class FilterBindingBackend(LibvirtXmlModel, tag="backend"):
    name: str = attr(name="name")


class FilterBinding(LibvirtXmlModel, tag="filterbinding"):
    """``<filterbinding>``: which filter guards which network device."""

    owner: FilterBindingOwner = element(tag="owner")
    portdev: FilterBindingPortdev = element(tag="portdev")
    linkdev: FilterBindingLinkdev | None = element(tag="linkdev", default=None)
    mac: FilterBindingMac = element(tag="mac")
    filterref: FilterRef = element(tag="filterref")
    backend: FilterBindingBackend | None = element(tag="backend", default=None)
