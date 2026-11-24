"""``<hostdev>``: host devices passed through to the guest.

One class per ``type`` (``pci``, ``usb``, ``scsi``, ...); ``Hostdev`` is their
plain union. The ``mode`` attribute (``subsystem``, or ``capabilities`` for
``storage``, ``misc`` and ``net``) follows from the type and is kept as written.

See https://libvirt.org/formatdomain.html#host-device-assignment
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.network import Route
from libvirtpy.xml._shared.storage import HostPciAddress, ScsiAdapter
from libvirtpy.xml._types import OnOff, PresenceFlag, Uuid, YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi, DeviceBoot
from libvirtpy.xml.domain.devices.interface import (
    HostdevProduct,
    HostdevVendor,
    InterfaceIp,
    InterfaceRom,
    InterfaceTeaming,
)
from libvirtpy.xml.domain.storage_source import Initiator, NetworkAuth

__all__ = [
    "Hostdev",
    "HostdevDriver",
    "MdevHostdev",
    "MiscHostdev",
    "NetHostdev",
    "PciHostdev",
    "ScsiHostHostdev",
    "ScsiHostdev",
    "StorageHostdev",
    "UsbHostdev",
]

StartupPolicy = Literal["mandatory", "requisite", "optional"]


class HostdevDriver(LibvirtXmlModel, tag="driver"):
    """``<driver>``: which host driver binds the device."""

    name: Literal["kvm", "vfio", "xen"] | None = attr(name="name", default=None)
    model: str | None = attr(name="model", default=None)
    iommufd: YesNo | None = attr(name="iommufd", default=None)


class _HostdevBase(LibvirtXmlModel, tag="hostdev"):
    """Fields every hostdev type has."""

    mode: Literal["subsystem", "capabilities"] | None = attr(name="mode", default=None)
    managed: YesNo | None = attr(name="managed", default=None)
    rom: InterfaceRom | None = element(tag="rom", default=None)
    readonly: PresenceFlag | None = element(tag="readonly", default=None)
    shareable: PresenceFlag | None = element(tag="shareable", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
    boot: DeviceBoot | None = element(tag="boot", default=None)


class PciSource(LibvirtXmlModel, tag="source"):
    start_policy: StartupPolicy | None = attr(name="startupPolicy", default=None)
    write_filtering: YesNo | None = attr(name="writeFiltering", default=None)
    address: HostPciAddress = element(tag="address")


class PciHostdev(_HostdevBase, tag="hostdev"):
    """``type='pci'``: a PCI device, optionally with a vfio display."""

    type: Literal["pci"] = attr(name="type")
    ramfb: OnOff | None = attr(name="ramfb", default=None)
    display: OnOff | None = attr(name="display", default=None)
    driver: HostdevDriver | None = element(tag="driver", default=None)
    teaming: InterfaceTeaming | None = element(tag="teaming", default=None)
    source: PciSource | None = element(tag="source", default=None)


class UsbAddress(LibvirtXmlModel, tag="address"):
    """``<address>`` of a host USB device: bus plus device or port."""

    bus: str = attr(name="bus")
    device: str | None = attr(name="device", default=None)
    port: str | None = attr(name="port", default=None)


class UsbSource(LibvirtXmlModel, tag="source"):
    start_policy: StartupPolicy | None = attr(name="startupPolicy", default=None)
    guest_reset: Literal["off", "uninitialized", "on"] | None = attr(
        name="guestReset", default=None
    )
    vendor: HostdevVendor | None = element(tag="vendor", default=None)
    product: HostdevProduct | None = element(tag="product", default=None)
    address: UsbAddress | None = element(tag="address", default=None)


class UsbHostdev(_HostdevBase, tag="hostdev"):
    """``type='usb'``: a USB device, by vendor/product or by address."""

    type: Literal["usb"] = attr(name="type")
    source: UsbSource | None = element(tag="source", default=None)


class ScsiAddress(LibvirtXmlModel, tag="address"):
    bus: str = attr(name="bus")
    target: str = attr(name="target")
    unit: str = attr(name="unit")


class ScsiHost(LibvirtXmlModel, tag="host"):
    """``<host>``: an iSCSI portal."""

    name: str = attr(name="name")
    port: int | None = attr(name="port", default=None, ge=0, le=65535)


class ScsiSource(LibvirtXmlModel, tag="source"):
    """``<source>`` of a SCSI hostdev: a local adapter or an iSCSI target."""

    protocol: Literal["adapter", "iscsi"] | None = attr(name="protocol", default=None)
    name: str | None = attr(name="name", default=None)
    adapter: ScsiAdapter | None = element(tag="adapter", default=None)
    address: ScsiAddress | None = element(tag="address", default=None)
    hosts: list[ScsiHost] = element(tag="host", default_factory=list)
    auth: NetworkAuth | None = element(tag="auth", default=None)
    initiator: Initiator | None = element(tag="initiator", default=None)


class ScsiHostdev(_HostdevBase, tag="hostdev"):
    """``type='scsi'``: a SCSI device."""

    type: Literal["scsi"] = attr(name="type")
    sgio: Literal["filtered", "unfiltered"] | None = attr(name="sgio", default=None)
    rawio: YesNo | None = attr(name="rawio", default=None)
    source: ScsiSource | None = element(tag="source", default=None)


class ScsiHostSource(LibvirtXmlModel, tag="source"):
    protocol: Literal["vhost"] = attr(name="protocol")
    wwpn: str = attr(name="wwpn")


class ScsiHostHostdev(_HostdevBase, tag="hostdev"):
    """``type='scsi_host'``: a vhost-scsi target."""

    type: Literal["scsi_host"] = attr(name="type")
    model: (
        Literal["virtio", "virtio-transitional", "virtio-non-transitional"] | None
    ) = attr(name="model", default=None)
    source: ScsiHostSource | None = element(tag="source", default=None)


class MdevAddress(LibvirtXmlModel, tag="address"):
    uuid: Uuid = attr(name="uuid")


class MdevSource(LibvirtXmlModel, tag="source"):
    address: MdevAddress = element(tag="address")


class MdevHostdev(_HostdevBase, tag="hostdev"):
    """``type='mdev'``: a mediated device."""

    type: Literal["mdev"] = attr(name="type")
    model: Literal["vfio-pci", "vfio-ccw", "vfio-ap"] = attr(name="model")
    ramfb: OnOff | None = attr(name="ramfb", default=None)
    display: OnOff | None = attr(name="display", default=None)
    source: MdevSource | None = element(tag="source", default=None)


class BlockSource(LibvirtXmlModel, tag="source"):
    block: str = element(tag="block", description="Host block device path.")


class StorageHostdev(_HostdevBase, tag="hostdev"):
    """``type='storage'``: a host block device (LXC)."""

    type: Literal["storage"] = attr(name="type")
    source: BlockSource | None = element(tag="source", default=None)


class CharSource(LibvirtXmlModel, tag="source"):
    char: str = element(tag="char", description="Host character device path.")


class MiscHostdev(_HostdevBase, tag="hostdev"):
    """``type='misc'``: a host character device (LXC)."""

    type: Literal["misc"] = attr(name="type")
    source: CharSource | None = element(tag="source", default=None)


class NetSource(LibvirtXmlModel, tag="source"):
    interface: str = element(tag="interface", description="Host network interface.")


class NetHostdev(_HostdevBase, tag="hostdev"):
    """``type='net'``: a host network interface moved into the container (LXC)."""

    type: Literal["net"] = attr(name="type")
    source: NetSource | None = element(tag="source", default=None)
    ips: list[InterfaceIp] = element(tag="ip", default_factory=list)
    routes: list[Route] = element(tag="route", default_factory=list)


Hostdev = (
    PciHostdev
    | UsbHostdev
    | ScsiHostdev
    | ScsiHostHostdev
    | MdevHostdev
    | StorageHostdev
    | MiscHostdev
    | NetHostdev
)
"""Any ``<hostdev>``; the variant is chosen by its ``type`` attribute."""
