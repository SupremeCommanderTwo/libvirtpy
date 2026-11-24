"""``<memballoon>``: the memory balloon device.

See https://libvirt.org/formatdomain.html#memory-balloon-device
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi, VirtioDriverOptions

__all__ = ["Memballoon", "MemballoonDriver", "MemballoonStats"]


class MemballoonStats(LibvirtXmlModel, tag="stats"):
    """``<stats>``: how often the guest reports memory statistics."""

    period: int = attr(name="period", ge=1, description="Seconds.")


class MemballoonDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>`` of a memory balloon: virtio options only."""


class Memballoon(LibvirtXmlModel, tag="memballoon"):
    """``<memballoon>``: lets the host reclaim guest memory."""

    model: Literal[
        "virtio", "virtio-transitional", "virtio-non-transitional", "xen", "none"
    ] = attr(name="model")
    autodeflate: OnOff | None = attr(
        name="autodeflate", default=None, description="Deflate on guest OOM."
    )
    free_page_reporting: OnOff | None = attr(name="freePageReporting", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
    stats: MemballoonStats | None = element(tag="stats", default=None)
    driver: MemballoonDriver | None = element(tag="driver", default=None)
