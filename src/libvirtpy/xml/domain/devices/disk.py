"""``<disk>``: hard disks, CD-ROMs and floppies.

``Disk`` is a plain union with one class per ``type`` of the disk (``file``,
``block``, ...), built from the storage mixins of
``libvirtpy.xml.domain.storage_source``. The same mixins build the
``<backingStore>`` chain.

See https://libvirt.org/formatdomain.html#hard-drives-floppy-disks-cdroms
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.storage import StorageEncryption
from libvirtpy.xml._types import OnOff, PresenceFlag, YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import (
    Alias,
    DeviceAcpi,
    DeviceBoot,
    DriverIothreads,
    VirtioDriverOptions,
)
from libvirtpy.xml.domain.storage_source import (
    BlockStorage,
    CtlStorage,
    DirStorage,
    DiskFormat,
    FileStorage,
    MetadataCache,
    NetworkAuth,
    NetworkStorage,
    NvmeStorage,
    VhostUserStorage,
    VhostVdpaStorage,
    VolumeStorage,
)

__all__ = [
    "BackingStore",
    "BlockBackingStore",
    "BlockDisk",
    "BlockIo",
    "BlockMirror",
    "CtlBackingStore",
    "CtlDisk",
    "CtlMirror",
    "DirBackingStore",
    "DirDisk",
    "DirMirror",
    "Disk",
    "DiskDriver",
    "DiskTarget",
    "FileBackingStore",
    "FileDisk",
    "FileMirror",
    "Geometry",
    "IoTune",
    "Mirror",
    "NetworkBackingStore",
    "NetworkDisk",
    "NetworkMirror",
    "NvmeBackingStore",
    "NvmeDisk",
    "NvmeMirror",
    "ThrottleFilter",
    "ThrottleFilters",
    "Transient",
    "VhostUserBackingStore",
    "VhostUserDisk",
    "VhostUserMirror",
    "VhostVdpaBackingStore",
    "VhostVdpaDisk",
    "VhostVdpaMirror",
    "VolumeBackingStore",
    "VolumeDisk",
    "VolumeMirror",
]


class StatisticEntry(LibvirtXmlModel, tag="statistic"):
    interval: int = attr(name="interval", ge=0)


class LatencyBin(LibvirtXmlModel, tag="bin"):
    start: int = attr(name="start", ge=0)


class LatencyHistogram(LibvirtXmlModel, tag="latency-histogram"):
    type: Literal["read", "write", "zone", "flush"] | None = attr(
        name="type", default=None
    )
    bins: list[LatencyBin] = element(tag="bin", default_factory=list)


class DiskStatistics(LibvirtXmlModel, tag="statistics"):
    statistics: list[StatisticEntry] = element(tag="statistic", default_factory=list)
    histograms: list[LatencyHistogram] = element(
        tag="latency-histogram", default_factory=list
    )


class DiskDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>``: the hypervisor driver and its tuning."""

    name: str | None = attr(name="name", default=None, description="e.g. ``qemu``.")
    type: str | None = attr(
        name="type", default=None, description="Image format, e.g. ``qcow2``."
    )
    cache: (
        Literal["default", "none", "writeback", "writethrough", "directsync", "unsafe"]
        | None
    ) = attr(name="cache", default=None)
    error_policy: Literal["stop", "report", "ignore", "enospace"] | None = attr(
        name="error_policy", default=None
    )
    rerror_policy: Literal["stop", "report", "ignore"] | None = attr(
        name="rerror_policy", default=None
    )
    io: Literal["threads", "native", "io_uring"] | None = attr(name="io", default=None)
    ioeventfd: OnOff | None = attr(name="ioeventfd", default=None)
    event_idx: OnOff | None = attr(name="event_idx", default=None)
    copy_on_read: OnOff | None = attr(name="copy_on_read", default=None)
    discard: Literal["unmap", "ignore"] | None = attr(name="discard", default=None)
    iothread: int | None = attr(name="iothread", default=None, ge=0)
    detect_zeroes: Literal["off", "on", "unmap"] | None = attr(
        name="detect_zeroes", default=None
    )
    discard_no_unref: OnOff | None = attr(name="discard_no_unref", default=None)
    queues: int | None = attr(name="queues", default=None, ge=1)
    queue_size: int | None = attr(name="queue_size", default=None, ge=1)
    metadata_cache: MetadataCache | None = element(tag="metadata_cache", default=None)
    iothreads: DriverIothreads | None = element(tag="iothreads", default=None)
    statistics: DiskStatistics | None = element(tag="statistics", default=None)


class DiskTarget(LibvirtXmlModel, tag="target"):
    """``<target>``: the device name and bus the guest sees."""

    dev: str = attr(name="dev", description="Guest device name, e.g. ``vda``.")
    bus: (
        Literal[
            "ide", "fdc", "scsi", "virtio", "xen", "usb", "uml", "sata", "sd", "nvme"
        ]
        | None
    ) = attr(name="bus", default=None)
    tray: Literal["open", "closed"] | None = attr(name="tray", default=None)
    removable: OnOff | None = attr(name="removable", default=None)
    rotation_rate: int | None = attr(name="rotation_rate", default=None, ge=1)
    dpofua: OnOff | None = attr(name="dpofua", default=None)


class BackendDomain(LibvirtXmlModel, tag="backenddomain"):
    """``<backenddomain>``: a Xen domain that serves the disk."""

    name: str = attr(name="name")


class Transient(LibvirtXmlModel, tag="transient"):
    """``<transient>``: changes are discarded when the guest stops."""

    share_backing: YesNo | None = attr(name="shareBacking", default=None)


class ThrottleFilter(LibvirtXmlModel, tag="throttlefilter"):
    group: str = attr(name="group")


class ThrottleFilters(LibvirtXmlModel, tag="throttlefilters"):
    """``<throttlefilters>``: I/O throttle groups applied to the disk."""

    filters: list[ThrottleFilter] = element(tag="throttlefilter", default_factory=list)


class IoTune(LibvirtXmlModel, tag="iotune"):
    """``<iotune>``: I/O limits; each element text is a plain number."""

    total_bytes_sec: int | None = element(tag="total_bytes_sec", default=None, ge=0)
    read_bytes_sec: int | None = element(tag="read_bytes_sec", default=None, ge=0)
    write_bytes_sec: int | None = element(tag="write_bytes_sec", default=None, ge=0)
    total_iops_sec: int | None = element(tag="total_iops_sec", default=None, ge=0)
    read_iops_sec: int | None = element(tag="read_iops_sec", default=None, ge=0)
    write_iops_sec: int | None = element(tag="write_iops_sec", default=None, ge=0)
    total_bytes_sec_max: int | None = element(
        tag="total_bytes_sec_max", default=None, ge=0
    )
    read_bytes_sec_max: int | None = element(
        tag="read_bytes_sec_max", default=None, ge=0
    )
    write_bytes_sec_max: int | None = element(
        tag="write_bytes_sec_max", default=None, ge=0
    )
    total_iops_sec_max: int | None = element(
        tag="total_iops_sec_max", default=None, ge=0
    )
    read_iops_sec_max: int | None = element(tag="read_iops_sec_max", default=None, ge=0)
    write_iops_sec_max: int | None = element(
        tag="write_iops_sec_max", default=None, ge=0
    )
    size_iops_sec: int | None = element(tag="size_iops_sec", default=None, ge=0)
    group_name: str | None = element(tag="group_name", default=None)
    total_bytes_sec_max_length: int | None = element(
        tag="total_bytes_sec_max_length", default=None, ge=0
    )
    read_bytes_sec_max_length: int | None = element(
        tag="read_bytes_sec_max_length", default=None, ge=0
    )
    write_bytes_sec_max_length: int | None = element(
        tag="write_bytes_sec_max_length", default=None, ge=0
    )
    total_iops_sec_max_length: int | None = element(
        tag="total_iops_sec_max_length", default=None, ge=0
    )
    read_iops_sec_max_length: int | None = element(
        tag="read_iops_sec_max_length", default=None, ge=0
    )
    write_iops_sec_max_length: int | None = element(
        tag="write_iops_sec_max_length", default=None, ge=0
    )


class Geometry(LibvirtXmlModel, tag="geometry"):
    """``<geometry>``: the legacy cylinders/heads/sectors of the disk."""

    cyls: int = attr(name="cyls")
    heads: int = attr(name="heads")
    secs: int = attr(name="secs")
    trans: Literal["auto", "none", "lba"] | None = attr(name="trans", default=None)


class BlockIo(LibvirtXmlModel, tag="blockio"):
    """``<blockio>``: block sizes the guest sees."""

    logical_block_size: int | None = attr(name="logical_block_size", default=None)
    physical_block_size: int | None = attr(name="physical_block_size", default=None)
    discard_granularity: int | None = attr(name="discard_granularity", default=None)


class _BackingStoreBase(LibvirtXmlModel, tag="backingStore"):
    """Fields of every ``<backingStore>``; an empty one ends the chain."""

    index: int | None = attr(name="index", default=None, ge=1)
    format: DiskFormat | None = element(tag="format", default=None)
    backing_store: BackingStore | None = element(tag="backingStore", default=None)


class FileBackingStore(_BackingStoreBase, FileStorage, tag="backingStore"):
    """A ``<backingStore>`` that is a file; also an empty, chain-ending one."""


class BlockBackingStore(_BackingStoreBase, BlockStorage, tag="backingStore"):
    """A ``<backingStore type='block'>``."""


class DirBackingStore(_BackingStoreBase, DirStorage, tag="backingStore"):
    """A ``<backingStore type='dir'>``."""


class NetworkBackingStore(_BackingStoreBase, NetworkStorage, tag="backingStore"):
    """A ``<backingStore type='network'>``."""


class VolumeBackingStore(_BackingStoreBase, VolumeStorage, tag="backingStore"):
    """A ``<backingStore type='volume'>``."""


class NvmeBackingStore(_BackingStoreBase, NvmeStorage, tag="backingStore"):
    """A ``<backingStore type='nvme'>``."""


class VhostUserBackingStore(_BackingStoreBase, VhostUserStorage, tag="backingStore"):
    """A ``<backingStore type='vhostuser'>``."""


class VhostVdpaBackingStore(_BackingStoreBase, VhostVdpaStorage, tag="backingStore"):
    """A ``<backingStore type='vhostvdpa'>``."""


class CtlBackingStore(_BackingStoreBase, CtlStorage, tag="backingStore"):
    """A ``<backingStore type='ctl'>``."""


BackingStore = (
    FileBackingStore
    | BlockBackingStore
    | DirBackingStore
    | NetworkBackingStore
    | VolumeBackingStore
    | NvmeBackingStore
    | VhostUserBackingStore
    | VhostVdpaBackingStore
    | CtlBackingStore
)
"""Any ``<backingStore>``; the variant is chosen by its ``type`` attribute."""


class _MirrorBase(LibvirtXmlModel, tag="mirror"):
    """``<mirror>``: a running block copy or active commit of the disk."""

    job: Literal["copy", "active-commit"] | None = attr(name="job", default=None)
    ready: Literal["yes", "abort", "pivot"] | None = attr(name="ready", default=None)
    file: str | None = attr(
        name="file", default=None, description="Target file of a ``type='file'`` copy."
    )
    format: str | None = attr(
        name="format", default=None, description="Image format of the target."
    )
    format_info: DiskFormat | None = element(tag="format", default=None)
    backing_store: BackingStore | None = element(tag="backingStore", default=None)


class FileMirror(_MirrorBase, FileStorage, tag="mirror"):
    """A ``<mirror>`` that is a file."""


class BlockMirror(_MirrorBase, BlockStorage, tag="mirror"):
    """A ``<mirror type='block'>``."""


class DirMirror(_MirrorBase, DirStorage, tag="mirror"):
    """A ``<mirror type='dir'>``."""


class NetworkMirror(_MirrorBase, NetworkStorage, tag="mirror"):
    """A ``<mirror type='network'>``."""


class VolumeMirror(_MirrorBase, VolumeStorage, tag="mirror"):
    """A ``<mirror type='volume'>``."""


class NvmeMirror(_MirrorBase, NvmeStorage, tag="mirror"):
    """A ``<mirror type='nvme'>``."""


class VhostUserMirror(_MirrorBase, VhostUserStorage, tag="mirror"):
    """A ``<mirror type='vhostuser'>``."""


class VhostVdpaMirror(_MirrorBase, VhostVdpaStorage, tag="mirror"):
    """A ``<mirror type='vhostvdpa'>``."""


class CtlMirror(_MirrorBase, CtlStorage, tag="mirror"):
    """A ``<mirror type='ctl'>``."""


Mirror = (
    FileMirror
    | BlockMirror
    | DirMirror
    | NetworkMirror
    | VolumeMirror
    | NvmeMirror
    | VhostUserMirror
    | VhostVdpaMirror
    | CtlMirror
)
"""Any ``<mirror>``; the variant is chosen by its ``type`` attribute."""


class _DiskBase(LibvirtXmlModel, tag="disk"):
    """Fields of every ``<disk>``, whatever its ``type``."""

    device: Literal["floppy", "disk", "cdrom", "lun"] | None = attr(
        name="device", default=None
    )
    model: (
        Literal[
            "virtio",
            "virtio-transitional",
            "virtio-non-transitional",
            "usb-storage",
            "usb-bot",
        ]
        | None
    ) = attr(name="model", default=None)
    snapshot: Literal["no", "internal", "external", "manual"] | None = attr(
        name="snapshot", default=None
    )
    rawio: YesNo | None = attr(name="rawio", default=None, description="``lun`` only.")
    sgio: Literal["filtered", "unfiltered"] | None = attr(
        name="sgio", default=None, description="``lun`` only."
    )
    driver: DiskDriver | None = element(tag="driver", default=None)
    target: DiskTarget | None = element(tag="target", default=None)
    backing_store: BackingStore | None = element(tag="backingStore", default=None)
    mirror: Mirror | None = element(tag="mirror", default=None)
    auth: NetworkAuth | None = element(tag="auth", default=None)
    boot: DeviceBoot | None = element(tag="boot", default=None)
    backend_domain: BackendDomain | None = element(tag="backenddomain", default=None)
    readonly: PresenceFlag | None = element(tag="readonly", default=None)
    shareable: PresenceFlag | None = element(tag="shareable", default=None)
    transient: Transient | None = element(tag="transient", default=None)
    serial: str | None = element(tag="serial", default=None)
    encryption: StorageEncryption | None = element(tag="encryption", default=None)
    throttle_filters: ThrottleFilters | None = element(
        tag="throttlefilters", default=None
    )
    iotune: IoTune | None = element(tag="iotune", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
    geometry: Geometry | None = element(tag="geometry", default=None)
    blockio: BlockIo | None = element(tag="blockio", default=None)
    wwn: str | None = element(tag="wwn", default=None)
    vendor: str | None = element(tag="vendor", default=None)
    product: str | None = element(tag="product", default=None)


class FileDisk(_DiskBase, FileStorage, tag="disk"):
    """A ``<disk>`` backed by a file; also a disk without ``type``."""


class BlockDisk(_DiskBase, BlockStorage, tag="disk"):
    """A ``<disk type='block'>``: a host block device."""


class DirDisk(_DiskBase, DirStorage, tag="disk"):
    """A ``<disk type='dir'>``: a host directory."""


class NetworkDisk(_DiskBase, NetworkStorage, tag="disk"):
    """A ``<disk type='network'>``: a remote image."""


class VolumeDisk(_DiskBase, VolumeStorage, tag="disk"):
    """A ``<disk type='volume'>``: a storage pool volume."""


class NvmeDisk(_DiskBase, NvmeStorage, tag="disk"):
    """A ``<disk type='nvme'>``: a host NVMe namespace. Since 6.0.0."""


class VhostUserDisk(_DiskBase, VhostUserStorage, tag="disk"):
    """A ``<disk type='vhostuser'>``. Since 7.1.0."""


class VhostVdpaDisk(_DiskBase, VhostVdpaStorage, tag="disk"):
    """A ``<disk type='vhostvdpa'>``. Since 9.8.0."""


class CtlDisk(_DiskBase, CtlStorage, tag="disk"):
    """A ``<disk type='ctl'>``: a FreeBSD CTL LUN (bhyve). Since 12.0.0."""


Disk = (
    FileDisk
    | BlockDisk
    | DirDisk
    | NetworkDisk
    | VolumeDisk
    | NvmeDisk
    | VhostUserDisk
    | VhostVdpaDisk
    | CtlDisk
)
"""Any ``<disk>``; the variant is chosen by its ``type`` attribute."""

# The chain refers to ``BackingStore``, which is defined after its members.
FileBackingStore.model_rebuild()
BlockBackingStore.model_rebuild()
DirBackingStore.model_rebuild()
NetworkBackingStore.model_rebuild()
VolumeBackingStore.model_rebuild()
NvmeBackingStore.model_rebuild()
VhostUserBackingStore.model_rebuild()
VhostVdpaBackingStore.model_rebuild()
CtlBackingStore.model_rebuild()
