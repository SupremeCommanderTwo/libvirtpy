"""Elements shared by many devices: ``<alias>``, ``<boot>``, ``<acpi>``.

See https://libvirt.org/formatdomain.html#devices
"""

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff

__all__ = [
    "Alias",
    "DeviceAcpi",
    "DeviceBoot",
    "DriverIothread",
    "DriverIothreadQueue",
    "DriverIothreads",
    "VirtioDriverOptions",
]


class Alias(LibvirtXmlModel, tag="alias"):
    """``<alias>``: the device's name. User aliases start with ``ua-``."""

    name: str = attr(name="name")


class DeviceBoot(LibvirtXmlModel, tag="boot"):
    """``<boot>`` in a device: its place in the boot order."""

    order: int = attr(name="order", ge=1)
    loadparm: str | None = attr(
        name="loadparm",
        default=None,
        pattern=r"^[a-zA-Z0-9.\s]{1,8}$",
        description="s390 boot selection.",
    )


class DeviceAcpi(LibvirtXmlModel, tag="acpi"):
    """``<acpi>`` in a device: its ACPI index or NUMA nodes."""

    index: int | None = attr(name="index", default=None, ge=0)
    nodeset: str | None = attr(name="nodeset", default=None)


class VirtioDriverOptions(LibvirtXmlModel):
    """Base for ``<driver>`` elements of virtio devices: their common attributes.

    See https://libvirt.org/formatdomain.html#virtio-related-options
    """

    iommu: OnOff | None = attr(name="iommu", default=None)
    ats: OnOff | None = attr(name="ats", default=None)
    packed: OnOff | None = attr(name="packed", default=None)
    page_per_vq: OnOff | None = attr(name="page_per_vq", default=None)


class DriverIothreadQueue(LibvirtXmlModel, tag="queue"):
    """``<queue>``: a device queue served by the enclosing I/O thread."""

    id: int = attr(name="id", ge=0)


class DriverIothread(LibvirtXmlModel, tag="iothread"):
    """``<iothread>`` in a ``<driver>``: one I/O thread and its queues."""

    id: int = attr(name="id", ge=0)
    queues: list[DriverIothreadQueue] = element(tag="queue", default_factory=list)


class DriverIothreads(LibvirtXmlModel, tag="iothreads"):
    """``<iothreads>`` in a ``<driver>``: map queues to I/O threads."""

    iothreads: list[DriverIothread] = element(tag="iothread", default_factory=list)
