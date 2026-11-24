"""``<iommu>``: a guest IOMMU.

See https://libvirt.org/formatdomain.html#iommu-devices
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff, SizeUnit
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi

__all__ = ["Iommu", "IommuDriver", "IommuGranule"]


class IommuGranule(LibvirtXmlModel, tag="granule"):
    """``<granule>``: the translation granule size (``host`` or an explicit size)."""

    mode: Literal["host"] | None = attr(name="mode", default=None)
    size: int | None = attr(name="size", default=None, ge=0)
    unit: SizeUnit | None = attr(name="unit", default=None)


class IommuDriver(LibvirtXmlModel, tag="driver"):
    """``<driver>``: options of the emulated IOMMU."""

    intremap: OnOff | None = attr(name="intremap", default=None)
    caching_mode: OnOff | None = attr(name="caching_mode", default=None)
    eim: OnOff | None = attr(name="eim", default=None)
    iotlb: OnOff | None = attr(name="iotlb", default=None)
    aw_bits: int | None = attr(name="aw_bits", default=None, ge=0, le=255)
    dma_translation: OnOff | None = attr(name="dma_translation", default=None)
    xtsup: OnOff | None = attr(name="xtsup", default=None)
    passthrough: OnOff | None = attr(name="passthrough", default=None)
    pci_bus: int | None = attr(name="pciBus", default=None, ge=0)
    accel: OnOff | None = attr(name="accel", default=None)
    ats: OnOff | None = attr(name="ats", default=None)
    ril: OnOff | None = attr(name="ril", default=None)
    ssidsize: int | None = attr(name="ssidsize", default=None)
    oas: int | None = attr(name="oas", default=None)
    cmdqv: OnOff | None = attr(name="cmdqv", default=None)
    granule: IommuGranule | None = element(tag="granule", default=None)


class Iommu(LibvirtXmlModel, tag="iommu"):
    """``<iommu>``: an IOMMU device."""

    model: Literal["intel", "smmuv3", "virtio", "amd"] = attr(name="model")
    driver: IommuDriver | None = element(tag="driver", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
