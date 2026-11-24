"""``<controller>``: buses that other devices attach to.

One model per controller ``type``; ``Controller`` is their union (see
``libvirtpy.xml.domain.devices.address`` for why it is a plain union).

See https://libvirt.org/formatdomain.html#controllers
"""

from typing import Literal

from pydantic import Field
from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import HexNumber, OnOff, SizeUnit
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import (
    Alias,
    DeviceAcpi,
    DriverIothreads,
    VirtioDriverOptions,
)

__all__ = [
    "CcidController",
    "Controller",
    "ControllerDriver",
    "FdcController",
    "IdeController",
    "IsaController",
    "NvmeController",
    "PciController",
    "PciControllerModel",
    "PciControllerTarget",
    "PciHole64",
    "SataController",
    "ScsiController",
    "UsbController",
    "UsbMaster",
    "VirtioSerialController",
    "XenbusController",
]


class ControllerDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>`` of a controller: queues and I/O threads."""

    queues: int | None = attr(name="queues", default=None, ge=0)
    cmd_per_lun: int | None = attr(name="cmd_per_lun", default=None, ge=0)
    max_sectors: int | None = attr(name="max_sectors", default=None, ge=0)
    ioeventfd: OnOff | None = attr(name="ioeventfd", default=None)
    iothread: int | None = attr(name="iothread", default=None, ge=0)
    iothreads: DriverIothreads | None = element(tag="iothreads", default=None)


class _ControllerBase(LibvirtXmlModel, tag="controller"):
    """Fields every controller type has."""

    index: int | None = attr(
        name="index", default=None, ge=0, description="Bus number of this type."
    )
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
    driver: ControllerDriver | None = element(tag="driver", default=None)


class FdcController(_ControllerBase, tag="controller"):
    """``type='fdc'``: a floppy disk controller."""

    type: Literal["fdc"] = attr(name="type")


class SataController(_ControllerBase, tag="controller"):
    """``type='sata'``: a SATA (AHCI) controller."""

    type: Literal["sata"] = attr(name="type")


class CcidController(_ControllerBase, tag="controller"):
    """``type='ccid'``: a USB smartcard reader."""

    type: Literal["ccid"] = attr(name="type")


class IsaController(_ControllerBase, tag="controller"):
    """``type='isa'``: the ISA bus."""

    type: Literal["isa"] = attr(name="type")


class ScsiController(_ControllerBase, tag="controller"):
    """``type='scsi'``: a SCSI host adapter."""

    type: Literal["scsi"] = attr(name="type")
    model: (
        Literal[
            "auto",
            "buslogic",
            "lsilogic",
            "lsisas1068",
            "vmpvscsi",
            "ibmvscsi",
            "virtio-scsi",
            "lsisas1078",
            "virtio-transitional",
            "virtio-non-transitional",
            "ncr53c90",
            "dc390",
            "am53c974",
        ]
        | None
    ) = attr(name="model", default=None)


class UsbMaster(LibvirtXmlModel, tag="master"):
    """``<master>``: makes a USB 1 companion controller part of a USB 2 one."""

    startport: str = attr(name="startport")


class UsbController(_ControllerBase, tag="controller"):
    """``type='usb'``: a USB host controller."""

    type: Literal["usb"] = attr(name="type")
    model: (
        Literal[
            "piix3-uhci",
            "piix4-uhci",
            "ehci",
            "ich9-ehci1",
            "ich9-uhci1",
            "ich9-uhci2",
            "ich9-uhci3",
            "vt82c686b-uhci",
            "pci-ohci",
            "nec-xhci",
            "none",
            "qusb1",
            "qusb2",
            "qemu-xhci",
        ]
        | None
    ) = attr(name="model", default=None)
    ports: int | None = attr(name="ports", default=None, ge=0)
    master: UsbMaster | None = element(tag="master", default=None)


class IdeController(_ControllerBase, tag="controller"):
    """``type='ide'``: an IDE controller."""

    type: Literal["ide"] = attr(name="type")
    model: Literal["piix3", "piix4", "ich6"] | None = attr(name="model", default=None)


class PciControllerModel(LibvirtXmlModel, tag="model"):
    """``<model>`` of a PCI controller: the exact emulated device. Since 1.2.19."""

    name: Literal[
        "spapr-pci-host-bridge",
        "pci-bridge",
        "i82801b11-bridge",
        "pcie-pci-bridge",
        "ioh3420",
        "pcie-root-port",
        "x3130-upstream",
        "xio3130-downstream",
        "pxb",
        "pxb-pcie",
    ] = attr(name="name")


class PciControllerTarget(LibvirtXmlModel, tag="target"):
    """``<target>`` of a PCI controller: guest-visible settings."""

    chassis_nr: HexNumber | None = attr(name="chassisNr", default=None)
    chassis: HexNumber | None = attr(name="chassis", default=None)
    port: HexNumber | None = attr(name="port", default=None)
    bus_nr: HexNumber | None = attr(name="busNr", default=None)
    index: HexNumber | None = attr(name="index", default=None)
    hotplug: OnOff | None = attr(name="hotplug", default=None)
    mem_reserve: int | None = attr(
        name="memReserve", default=None, ge=0, description="KiB. Since 10.3.0."
    )
    node: int | None = element(
        tag="node", default=None, ge=0, description="NUMA node of an expander bus."
    )


class PciHole64(LibvirtXmlModel, tag="pcihole64"):
    """``<pcihole64>``: size of the 64-bit PCI hole. Since 1.1.2."""

    value: int = Field(ge=0, description="Element text: the size, in ``unit``.")
    unit: SizeUnit | None = attr(name="unit", default=None)


class PciController(_ControllerBase, tag="controller"):
    """``type='pci'``: a PCI or PCIe root, bridge, port or expander bus."""

    type: Literal["pci"] = attr(name="type")
    model: (
        Literal[
            "pci-root",
            "pcie-root",
            "pci-bridge",
            "dmi-to-pci-bridge",
            "pcie-to-pci-bridge",
            "pcie-root-port",
            "pcie-switch-upstream-port",
            "pcie-switch-downstream-port",
            "pci-expander-bus",
            "pcie-expander-bus",
        ]
        | None
    ) = attr(name="model", default=None)
    model_info: PciControllerModel | None = element(tag="model", default=None)
    target: PciControllerTarget | None = element(tag="target", default=None)
    pcihole64: PciHole64 | None = element(
        tag="pcihole64", default=None, description="Only on root controllers."
    )


class VirtioSerialController(_ControllerBase, tag="controller"):
    """``type='virtio-serial'``: ports for ``<channel>`` and ``<console>``."""

    type: Literal["virtio-serial"] = attr(name="type")
    model: (
        Literal["virtio", "virtio-transitional", "virtio-non-transitional"] | None
    ) = attr(name="model", default=None)
    ports: int | None = attr(name="ports", default=None, ge=0)
    vectors: int | None = attr(name="vectors", default=None, ge=0)


class XenbusController(_ControllerBase, tag="controller"):
    """``type='xenbus'``: the Xen paravirtual bus."""

    type: Literal["xenbus"] = attr(name="type")
    max_grant_frames: int | None = attr(name="maxGrantFrames", default=None, ge=0)
    max_event_channels: int | None = attr(name="maxEventChannels", default=None, ge=0)


class NvmeController(_ControllerBase, tag="controller"):
    """``type='nvme'``: an NVMe controller. Since 11.5.0."""

    type: Literal["nvme"] = attr(name="type")
    serial: str | None = element(tag="serial", default=None)


Controller = (
    FdcController
    | SataController
    | CcidController
    | IsaController
    | ScsiController
    | UsbController
    | IdeController
    | PciController
    | VirtioSerialController
    | XenbusController
    | NvmeController
)
"""Any ``<controller>``; the variant is chosen by its ``type`` attribute."""
