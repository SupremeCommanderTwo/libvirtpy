"""``<memory>`` as a device: hot-pluggable memory modules.

Not to be confused with the domain's ``<memory>`` (``libvirtpy.xml.domain.memory``).

See https://libvirt.org/formatdomain.html#memory-devices
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import PresenceFlag, ScaledInteger, Uuid, YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi, VirtioDriverOptions

__all__ = ["MemoryDevice", "MemoryDeviceSource", "MemoryDeviceTarget"]


class MemoryDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>`` of a memory device: virtio options only."""


class PageSize(ScaledInteger, tag="pagesize"):
    """``<pagesize>``: the host page size backing the module."""


class AlignSize(ScaledInteger, tag="alignsize"):
    """``<alignsize>``: alignment of a persistent memory backend."""


class MemoryDeviceSource(LibvirtXmlModel, tag="source"):
    """``<source>``: where the module's memory comes from."""

    pagesize: PageSize | None = element(tag="pagesize", default=None)
    nodemask: str | None = element(tag="nodemask", default=None)
    path: str | None = element(tag="path", default=None)
    alignsize: AlignSize | None = element(tag="alignsize", default=None)
    pmem: PresenceFlag | None = element(tag="pmem", default=None)


class TargetSize(ScaledInteger, tag="size"):
    """``<size>``: the size of the module."""


class TargetBlock(ScaledInteger, tag="block"):
    """``<block>``: the block size of a virtio-mem module."""


class TargetRequested(ScaledInteger, tag="requested"):
    """``<requested>``: the size requested of a virtio-mem module."""


class TargetCurrent(ScaledInteger, tag="current"):
    """``<current>``: the current size of a virtio-mem module."""


class LabelSize(ScaledInteger, tag="size"):
    """``<size>`` of the label area."""


class TargetLabel(LibvirtXmlModel, tag="label"):
    size: LabelSize = element(tag="size")


class TargetAddress(LibvirtXmlModel, tag="address"):
    """``<address>`` of a module: where it is mapped in guest memory."""

    base: str = attr(name="base")


class MemoryDeviceTarget(LibvirtXmlModel, tag="target"):
    """``<target>``: the module as the guest sees it."""

    dynamic_memslots: YesNo | None = attr(name="dynamicMemslots", default=None)
    size: TargetSize = element(tag="size")
    node: int | None = element(tag="node", default=None, ge=0)
    block: TargetBlock | None = element(tag="block", default=None)
    requested: TargetRequested | None = element(tag="requested", default=None)
    current: TargetCurrent | None = element(tag="current", default=None)
    label: TargetLabel | None = element(tag="label", default=None)
    readonly: PresenceFlag | None = element(tag="readonly", default=None)
    address: TargetAddress | None = element(tag="address", default=None)


class MemoryDevice(LibvirtXmlModel, tag="memory"):
    """``<memory>``: a ``dimm``, ``nvdimm``, ``virtio-pmem``, ``virtio-mem`` or
    ``sgx-epc`` module."""

    model: Literal["dimm", "nvdimm", "virtio-pmem", "virtio-mem", "sgx-epc"] = attr(
        name="model"
    )
    access: Literal["shared", "private"] | None = attr(name="access", default=None)
    discard: YesNo | None = attr(name="discard", default=None)
    uuid: Uuid | None = element(tag="uuid", default=None)
    driver: MemoryDriver | None = element(tag="driver", default=None)
    source: MemoryDeviceSource | None = element(tag="source", default=None)
    target: MemoryDeviceTarget = element(tag="target")
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
