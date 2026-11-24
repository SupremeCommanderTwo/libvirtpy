"""``<device>``: a host device, as listed by ``virsh nodedev-*``.

Each ``<capability type=...>`` is its own class; ``Capability`` is their plain
union (see ``libvirtpy.xml.domain.devices.address`` for why it is not a
discriminated union). Capabilities nested in a capability (``phys_function``,
``fc_host``, ``removable``, ...) are the union ``SubCapability``.

See https://libvirt.org/formatnode.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import Uuid

__all__ = [
    "Capability",
    "Device",
    "SubCapability",
]


class DeviceAddress(LibvirtXmlModel, tag="address"):
    """``<address>``: a PCI address."""

    domain: str | None = attr(name="domain", default=None)
    bus: str | None = attr(name="bus", default=None)
    slot: str | None = attr(name="slot", default=None)
    function: str | None = attr(name="function", default=None)


class IdText(LibvirtXmlModel):
    """Base of ``<vendor>`` and ``<product>``: a hex ``id`` and optional text."""

    value: str = ""
    id: str = attr(name="id", pattern=r"^(0x)?[0-9a-fA-F]+$")


class Vendor(IdText, tag="vendor"):
    """``<vendor>``: the vendor ID and name."""


class Product(IdText, tag="product"):
    """``<product>``: the product ID and name."""


# sub-capabilities


class PhysFunction(LibvirtXmlModel, tag="capability"):
    """``type='phys_function'``: the physical function of a virtual function."""

    type: Literal["phys_function"] = attr(name="type")
    address: DeviceAddress | None = element(tag="address", default=None)


class VirtFunctions(LibvirtXmlModel, tag="capability"):
    """``type='virt_functions'``: the virtual functions of a physical function."""

    type: Literal["virt_functions"] = attr(name="type")
    max_count: int | None = attr(name="maxCount", default=None, ge=0)
    addresses: list[DeviceAddress] = element(tag="address", default_factory=list)


class PciBridge(LibvirtXmlModel, tag="capability"):
    """``type='pci-bridge'`` or ``'cardbus-bridge'``."""

    type: Literal["pci-bridge", "cardbus-bridge"] = attr(name="type")


class MdevTypeInfo(LibvirtXmlModel, tag="type"):
    id: str = attr(name="id")
    name: str | None = element(tag="name", default=None)
    device_api: Literal["vfio-pci", "vfio-ccw", "vfio-ap"] = element(tag="deviceAPI")
    available_instances: int = element(tag="availableInstances", ge=0)


class MdevTypes(LibvirtXmlModel, tag="capability"):
    """``type='mdev_types'``: the mediated device types the device supports."""

    type: Literal["mdev_types"] = attr(name="type")
    types: list[MdevTypeInfo] = element(tag="type", default_factory=list)


class VpdField(LibvirtXmlModel, tag="vendor_field"):
    value: str = ""
    index: str = attr(name="index")


class VpdSystemField(LibvirtXmlModel, tag="system_field"):
    value: str = ""
    index: str = attr(name="index")


class VpdReadOnlyFields(LibvirtXmlModel, tag="fields"):
    access: Literal["readonly"] = attr(name="access")
    change_level: str | None = element(tag="change_level", default=None)
    manufacture_id: str | None = element(tag="manufacture_id", default=None)
    part_number: str | None = element(tag="part_number", default=None)
    serial_number: str | None = element(tag="serial_number", default=None)
    vendor_fields: list[VpdField] = element(tag="vendor_field", default_factory=list)


class VpdReadWriteFields(LibvirtXmlModel, tag="fields"):
    access: Literal["readwrite"] = attr(name="access")
    asset_tag: str | None = element(tag="asset_tag", default=None)
    vendor_fields: list[VpdField] = element(tag="vendor_field", default_factory=list)
    system_fields: list[VpdSystemField] = element(
        tag="system_field", default_factory=list
    )


class Vpd(LibvirtXmlModel, tag="capability"):
    """``type='vpd'``: the PCI vital product data. Since 7.9.0."""

    type: Literal["vpd"] = attr(name="type")
    name: str = element(tag="name")
    fields: list[VpdReadOnlyFields | VpdReadWriteFields] = element(
        tag="fields", default_factory=list
    )


class Cap80203(LibvirtXmlModel, tag="capability"):
    """``type='80203'``: an Ethernet interface."""

    type: Literal["80203"] = attr(name="type")


class Cap80211(LibvirtXmlModel, tag="capability"):
    """``type='80211'``: a wireless interface."""

    type: Literal["80211"] = attr(name="type")


class FcHost(LibvirtXmlModel, tag="capability"):
    """``type='fc_host'``: a Fibre Channel host."""

    type: Literal["fc_host"] = attr(name="type")
    wwnn: str = element(tag="wwnn")
    wwpn: str = element(tag="wwpn")
    fabric_wwn: str | None = element(tag="fabric_wwn", default=None)


class VportOps(LibvirtXmlModel, tag="capability"):
    """``type='vport_ops'``: virtual ports of a Fibre Channel host."""

    type: Literal["vport_ops"] = attr(name="type")
    max_vports: int = element(tag="max_vports", ge=0)
    vports: int = element(tag="vports", ge=0)


class FcRemotePort(LibvirtXmlModel, tag="capability"):
    """``type='fc_remote_port'``: a remote Fibre Channel port."""

    type: Literal["fc_remote_port"] = attr(name="type")
    rport: str = element(tag="rport")
    wwpn: str = element(tag="wwpn")


class Removable(LibvirtXmlModel, tag="capability"):
    """``type='removable'``: a storage device with removable media."""

    type: Literal["removable"] = attr(name="type")
    media_available: Literal["0", "1"] = element(tag="media_available")
    media_size: int = element(tag="media_size", ge=0)
    media_label: str | None = element(tag="media_label", default=None)
    logical_block_size: int | None = element(
        tag="logical_block_size", default=None, ge=0
    )
    num_blocks: int | None = element(tag="num_blocks", default=None, ge=0)


class Hotpluggable(LibvirtXmlModel, tag="capability"):
    """``type='hotpluggable'``: a storage device that can be unplugged."""

    type: Literal["hotpluggable"] = attr(name="type")


class CcwGroupMember(LibvirtXmlModel, tag="capability"):
    """``type='ccwgroup_member'``: a member of a CCW group device."""

    type: Literal["ccwgroup_member"] = attr(name="type")
    group_device: str = element(tag="group_device")


class QethGroup(LibvirtXmlModel, tag="capability"):
    """``type='qeth_generic'``, ``'qeth_layer2'`` or ``'qeth_layer3'``."""

    type: Literal["qeth_generic", "qeth_layer2", "qeth_layer3"] = attr(name="type")
    card_type: str = element(tag="card_type")
    chpid: str = element(tag="chpid")


SubCapability = (
    PhysFunction
    | VirtFunctions
    | PciBridge
    | MdevTypes
    | Vpd
    | Cap80203
    | Cap80211
    | FcHost
    | VportOps
    | FcRemotePort
    | Removable
    | Hotpluggable
    | CcwGroupMember
    | QethGroup
)
"""Any capability nested in another; chosen by its ``type`` attribute."""


# capabilities


class SystemHardware(LibvirtXmlModel, tag="hardware"):
    vendor: str | None = element(tag="vendor", default=None)
    version: str | None = element(tag="version", default=None)
    serial: str | None = element(tag="serial", default=None)
    uuid: Uuid = element(tag="uuid")


class SystemFirmware(LibvirtXmlModel, tag="firmware"):
    vendor: str | None = element(tag="vendor", default=None)
    version: str | None = element(tag="version", default=None)
    release_date: str | None = element(tag="release_date", default=None)


class SystemCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["system"] = attr(name="type")
    product: str | None = element(tag="product", default=None)
    hardware: SystemHardware = element(tag="hardware")
    firmware: SystemFirmware = element(tag="firmware")


class IommuGroup(LibvirtXmlModel, tag="iommuGroup"):
    number: int = attr(name="number", ge=0)
    addresses: list[DeviceAddress] = element(tag="address", default_factory=list)


class Numa(LibvirtXmlModel, tag="numa"):
    node: int | None = attr(name="node", default=None)


class PciExpressLink(LibvirtXmlModel, tag="link"):
    validity: Literal["cap", "sta"] = attr(name="validity")
    port: int | None = attr(name="port", default=None, ge=0)
    speed: str | None = attr(name="speed", default=None)
    width: int = attr(name="width", ge=0)


class PciExpress(LibvirtXmlModel, tag="pci-express"):
    links: list[PciExpressLink] = element(tag="link", default_factory=list)


class PciCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["pci"] = attr(name="type")
    class_: str | None = element(tag="class", default=None)
    domain: int = element(tag="domain", ge=0)
    bus: int = element(tag="bus", ge=0)
    slot: int = element(tag="slot", ge=0)
    function: int = element(tag="function", ge=0)
    product: Product = element(tag="product")
    vendor: Vendor = element(tag="vendor")
    capabilities: list[SubCapability] = element(tag="capability", default_factory=list)
    iommu_group: IommuGroup | None = element(tag="iommuGroup", default=None)
    numa: Numa | None = element(tag="numa", default=None)
    pci_express: PciExpress | None = element(tag="pci-express", default=None)


class UsbDeviceCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["usb_device"] = attr(name="type")
    bus: int = element(tag="bus", ge=0)
    device: int = element(tag="device", ge=0)
    # The schema requires <port>, but libvirt leaves it out for root hubs.
    port: int | None = element(tag="port", default=None, ge=0)
    product: Product = element(tag="product")
    vendor: Vendor = element(tag="vendor")


class UsbCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["usb"] = attr(name="type")
    number: int = element(tag="number", ge=0)
    class_: int = element(tag="class", ge=0)
    subclass: int = element(tag="subclass", ge=0)
    protocol: int = element(tag="protocol", ge=0)
    description: str | None = element(tag="description", default=None)


class NetLink(LibvirtXmlModel, tag="link"):
    speed: int | None = attr(name="speed", default=None, ge=0)
    state: str | None = attr(name="state", default=None)


class NetFeature(LibvirtXmlModel, tag="feature"):
    name: str = attr(name="name")


class NetCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["net"] = attr(name="type")
    interface: str = element(tag="interface")
    address: str | None = element(tag="address", default=None)
    link: NetLink | None = element(tag="link", default=None)
    features: list[NetFeature] = element(tag="feature", default_factory=list)
    capabilities: list[SubCapability] = element(tag="capability", default_factory=list)


class ScsiGenericCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["scsi_generic"] = attr(name="type")
    char: str = element(tag="char")


class ScsiHostCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["scsi_host"] = attr(name="type")
    host: int = element(tag="host", ge=0)
    unique_id: int | None = element(tag="unique_id", default=None, ge=0)
    capabilities: list[SubCapability] = element(tag="capability", default_factory=list)


class ScsiTargetCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["scsi_target"] = attr(name="type")
    target: str = element(tag="target")
    capabilities: list[SubCapability] = element(tag="capability", default_factory=list)


class ScsiCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["scsi"] = attr(name="type")
    host: int = element(tag="host", ge=0)
    bus: int = element(tag="bus", ge=0)
    target: int = element(tag="target", ge=0)
    lun: int = element(tag="lun", ge=0)
    device_type: str | None = element(tag="type", default=None)


class StorageCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["storage"] = attr(name="type")
    block: str = element(tag="block")
    bus: str | None = element(tag="bus", default=None)
    drive_type: str | None = element(tag="drive_type", default=None)
    model: str | None = element(tag="model", default=None)
    vendor: str | None = element(tag="vendor", default=None)
    serial: str | None = element(tag="serial", default=None)
    size: int | None = element(tag="size", default=None, ge=0)
    logical_block_size: int | None = element(
        tag="logical_block_size", default=None, ge=0
    )
    num_blocks: int | None = element(tag="num_blocks", default=None, ge=0)
    capabilities: list[SubCapability] = element(tag="capability", default_factory=list)


class DrmCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["drm"] = attr(name="type")
    device_type: Literal["primary", "control", "render"] = element(tag="type")


class MdevTypeId(LibvirtXmlModel, tag="type"):
    id: str = attr(name="id")


class MdevAttr(LibvirtXmlModel, tag="attr"):
    name: str = attr(name="name")
    value: str = attr(name="value")


class MdevCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["mdev"] = attr(name="type")
    mdev_type: MdevTypeId = element(tag="type")
    iommu_group: IommuGroup | None = element(tag="iommuGroup", default=None)
    uuid: Uuid | None = element(tag="uuid", default=None)
    parent_addr: str | None = element(tag="parent_addr", default=None)
    attrs: list[MdevAttr] = element(tag="attr", default_factory=list)


class CcwCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["ccw"] = attr(name="type")
    state: Literal["online", "offline"] | None = element(tag="state", default=None)
    cssid: str = element(tag="cssid")
    ssid: str = element(tag="ssid")
    devno: str = element(tag="devno")
    capabilities: list[SubCapability] = element(tag="capability", default_factory=list)


class CcwMember(LibvirtXmlModel, tag="ccw_device"):
    value: str = ""
    ref: str = attr(name="ref")


class CcwMembers(LibvirtXmlModel, tag="members"):
    devices: list[CcwMember] = element(tag="ccw_device", default_factory=list)


class CcwGroupCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["ccwgroup"] = attr(name="type")
    state: Literal["online", "offline"] | None = element(tag="state", default=None)
    cssid: str = element(tag="cssid")
    ssid: str = element(tag="ssid")
    devno: str = element(tag="devno")
    members: CcwMembers | None = element(tag="members", default=None)
    capabilities: list[SubCapability] = element(tag="capability", default_factory=list)


class ChannelDevAddr(LibvirtXmlModel, tag="channel_dev_addr"):
    cssid: str = element(tag="cssid")
    ssid: str = element(tag="ssid")
    devno: str = element(tag="devno")


class CssCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["css"] = attr(name="type")
    cssid: str = element(tag="cssid")
    ssid: str = element(tag="ssid")
    devno: str = element(tag="devno")
    channel_dev_addr: ChannelDevAddr | None = element(
        tag="channel_dev_addr", default=None
    )
    capabilities: list[SubCapability] = element(tag="capability", default_factory=list)


class VdpaCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["vdpa"] = attr(name="type")
    chardev: str = element(tag="chardev")


class ApCardCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["ap_card"] = attr(name="type")
    ap_adapter: str = element(tag="ap-adapter")


class ApQueueCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["ap_queue"] = attr(name="type")
    ap_adapter: str = element(tag="ap-adapter")
    ap_domain: str = element(tag="ap-domain")


class ApMatrixCapability(LibvirtXmlModel, tag="capability"):
    type: Literal["ap_matrix"] = attr(name="type")
    capabilities: list[SubCapability] = element(tag="capability", default_factory=list)


Capability = (
    SystemCapability
    | PciCapability
    | UsbDeviceCapability
    | UsbCapability
    | NetCapability
    | ScsiGenericCapability
    | ScsiHostCapability
    | ScsiTargetCapability
    | ScsiCapability
    | StorageCapability
    | DrmCapability
    | MdevCapability
    | CcwCapability
    | CcwGroupCapability
    | CssCapability
    | VdpaCapability
    | ApCardCapability
    | ApQueueCapability
    | ApMatrixCapability
)
"""Any ``<capability>`` of a node device; chosen by its ``type`` attribute."""


class DeviceNode(LibvirtXmlModel, tag="devnode"):
    value: str = ""
    type: Literal["dev", "link"] = attr(name="type")


class DeviceParent(LibvirtXmlModel, tag="parent"):
    value: str = ""
    wwnn: str | None = attr(name="wwnn", default=None)
    wwpn: str | None = attr(name="wwpn", default=None)
    fabric_wwn: str | None = attr(name="fabric_wwn", default=None)


class DeviceDriver(LibvirtXmlModel, tag="driver"):
    name: str = element(tag="name")


class Device(LibvirtXmlModel, tag="device"):
    """``<device>``: a host device and what it can do."""

    name: str = element(tag="name")
    path: str | None = element(tag="path", default=None)
    devnodes: list[DeviceNode] = element(tag="devnode", default_factory=list)
    parent: DeviceParent | None = element(tag="parent", default=None)
    driver: DeviceDriver | None = element(tag="driver", default=None)
    capabilities: list[Capability] = element(tag="capability", default_factory=list)
