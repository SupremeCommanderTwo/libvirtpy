"""``<address>``: where a device sits on its bus.

Address numbers are kept as strings exactly as written (``0x1f`` or ``31``):
libvirt accepts hex and decimal forms, and converting them would change the
document on a round trip.

``Address`` is a plain union, not a ``Field(discriminator=...)`` one, like
every variant union in libvirtpy. With pydantic-xml 2.22 a discriminated
union crashes on serializing a ``None`` field, and in a list it silently
drops the element with an unknown ``type`` and every element after it. With
a plain union the ``type`` literals still make exactly one variant match, and
an unknown ``type`` is a validation error.

See https://libvirt.org/formatdomain.html#device-addresses
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import HexNumber, OnOff

__all__ = [
    "Address",
    "CcidAddress",
    "CcwAddress",
    "DimmAddress",
    "DriveAddress",
    "IsaAddress",
    "PciAddress",
    "SpaprVioAddress",
    "UnassignedAddress",
    "UsbAddress",
    "VirtioMmioAddress",
    "VirtioSerialAddress",
    "Zpci",
]


class Zpci(LibvirtXmlModel, tag="zpci"):
    """``<zpci>``: s390 PCI identifiers. Since 4.10.0."""

    uid: HexNumber | None = attr(name="uid", default=None)
    fid: HexNumber | None = attr(name="fid", default=None)


class PciAddress(LibvirtXmlModel, tag="address"):
    """``type='pci'``: a PCI ``domain:bus:slot.function`` address."""

    type: Literal["pci"] = attr(name="type")
    domain: HexNumber | None = attr(name="domain", default=None)
    bus: HexNumber | None = attr(name="bus", default=None)
    slot: HexNumber | None = attr(name="slot", default=None)
    function: HexNumber | None = attr(name="function", default=None)
    multifunction: OnOff | None = attr(name="multifunction", default=None)
    zpci: Zpci | None = element(tag="zpci", default=None)


class DriveAddress(LibvirtXmlModel, tag="address"):
    """``type='drive'``: a disk on an IDE, SCSI, SATA or floppy controller."""

    type: Literal["drive"] = attr(name="type")
    controller: HexNumber | None = attr(name="controller", default=None)
    bus: HexNumber | None = attr(name="bus", default=None)
    target: HexNumber | None = attr(name="target", default=None)
    unit: HexNumber | None = attr(name="unit", default=None)


class VirtioSerialAddress(LibvirtXmlModel, tag="address"):
    """``type='virtio-serial'``: a port on a virtio-serial controller."""

    type: Literal["virtio-serial"] = attr(name="type")
    controller: HexNumber = attr(name="controller")
    bus: HexNumber | None = attr(name="bus", default=None)
    port: HexNumber | None = attr(name="port", default=None)


class CcidAddress(LibvirtXmlModel, tag="address"):
    """``type='ccid'``: a slot on a smartcard (CCID) controller."""

    type: Literal["ccid"] = attr(name="type")
    controller: HexNumber = attr(name="controller")
    slot: HexNumber | None = attr(name="slot", default=None)


class UsbAddress(LibvirtXmlModel, tag="address"):
    """``type='usb'``: a USB bus and port, e.g. ``port='1.2'`` behind a hub."""

    type: Literal["usb"] = attr(name="type")
    bus: HexNumber = attr(name="bus")
    port: str | None = attr(name="port", default=None)


class SpaprVioAddress(LibvirtXmlModel, tag="address"):
    """``type='spapr-vio'``: a PowerPC sPAPR VIO device."""

    type: Literal["spapr-vio"] = attr(name="type")
    reg: HexNumber | None = attr(name="reg", default=None)


class CcwAddress(LibvirtXmlModel, tag="address"):
    """``type='ccw'``: an s390 channel I/O device."""

    type: Literal["ccw"] = attr(name="type")
    cssid: HexNumber | None = attr(name="cssid", default=None)
    ssid: HexNumber | None = attr(name="ssid", default=None)
    devno: HexNumber | None = attr(name="devno", default=None)


class IsaAddress(LibvirtXmlModel, tag="address"):
    """``type='isa'``: an ISA I/O port and IRQ."""

    type: Literal["isa"] = attr(name="type")
    iobase: HexNumber | None = attr(name="iobase", default=None)
    irq: HexNumber | None = attr(name="irq", default=None)


class VirtioMmioAddress(LibvirtXmlModel, tag="address"):
    """``type='virtio-mmio'``: a memory mapped virtio device."""

    type: Literal["virtio-mmio"] = attr(name="type")


class DimmAddress(LibvirtXmlModel, tag="address"):
    """``type='dimm'``: a memory module slot."""

    type: Literal["dimm"] = attr(name="type")
    slot: int | None = attr(name="slot", default=None, ge=0)
    base: HexNumber | None = attr(name="base", default=None)


class UnassignedAddress(LibvirtXmlModel, tag="address"):
    """``type='unassigned'``: a host device the guest does not see. Since 6.0.0."""

    type: Literal["unassigned"] = attr(name="type")


Address = (
    PciAddress
    | DriveAddress
    | VirtioSerialAddress
    | CcidAddress
    | UsbAddress
    | SpaprVioAddress
    | CcwAddress
    | IsaAddress
    | VirtioMmioAddress
    | DimmAddress
    | UnassignedAddress
)
"""Any device ``<address>``; the variant is chosen by its ``type`` attribute."""
