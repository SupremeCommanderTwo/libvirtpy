"""``<volume>``: a storage volume.

See https://libvirt.org/formatstorage.html#storage-volume-xml
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.storage import (
    Allocation,
    Capacity,
    Permissions,
    StorageEncryption,
    Timestamps,
)
from libvirtpy.xml._types import PresenceFlag, ScaledInteger

__all__ = [
    "Volume",
    "VolumeBackingStore",
    "VolumeFeatures",
    "VolumeFormat",
    "VolumePhysical",
    "VolumeSource",
    "VolumeTarget",
]


class VolumePhysical(ScaledInteger, tag="physical"):
    """``<physical>``: the size of the volume on the host file system."""


class VolumeExtent(LibvirtXmlModel, tag="extent"):
    start: int = attr(name="start", ge=0)
    end: int = attr(name="end", ge=0)


class VolumeSourceDevice(LibvirtXmlModel, tag="device"):
    path: str = attr(name="path")
    extents: list[VolumeExtent] = element(tag="extent", default_factory=list)


class VolumeSource(LibvirtXmlModel, tag="source"):
    """``<source>``: the devices a volume was allocated from."""

    devices: list[VolumeSourceDevice] = element(tag="device", default_factory=list)


class VolumeFormat(LibvirtXmlModel, tag="format"):
    type: str = attr(name="type", description="e.g. ``raw`` or ``qcow2``.")


class ClusterSize(ScaledInteger, tag="clusterSize"):
    """``<clusterSize>``: the qcow2 cluster size."""


class VolumeFeatures(LibvirtXmlModel, tag="features"):
    """``<features>`` of a qcow2 volume."""

    lazy_refcounts: PresenceFlag | None = element(tag="lazy_refcounts", default=None)
    extended_l2: PresenceFlag | None = element(tag="extended_l2", default=None)


class VolumeTarget(LibvirtXmlModel, tag="target"):
    """``<target>``: how the volume looks on the host."""

    path: str | None = element(tag="path", default=None)
    format: VolumeFormat | None = element(tag="format", default=None)
    permissions: Permissions | None = element(tag="permissions", default=None)
    timestamps: Timestamps | None = element(tag="timestamps", default=None)
    encryption: StorageEncryption | None = element(tag="encryption", default=None)
    compat: str | None = element(tag="compat", default=None)
    nocow: PresenceFlag | None = element(tag="nocow", default=None)
    cluster_size: ClusterSize | None = element(tag="clusterSize", default=None)
    features: VolumeFeatures | None = element(tag="features", default=None)


class VolumeBackingStore(LibvirtXmlModel, tag="backingStore"):
    """``<backingStore>``: the image this volume is a copy-on-write layer of."""

    path: str = element(tag="path")
    format: VolumeFormat | None = element(tag="format", default=None)
    permissions: Permissions | None = element(tag="permissions", default=None)
    timestamps: Timestamps | None = element(tag="timestamps", default=None)


class Volume(LibvirtXmlModel, tag="volume"):
    """``<volume>``: a storage volume."""

    type: Literal["file", "block", "dir", "network", "netdir"] | None = attr(
        name="type", default=None
    )
    name: str = element(tag="name")
    key: str | None = element(tag="key", default=None)
    source: VolumeSource | None = element(tag="source", default=None)
    capacity: Capacity | None = element(tag="capacity", default=None)
    allocation: Allocation | None = element(tag="allocation", default=None)
    physical: VolumePhysical | None = element(tag="physical", default=None)
    target: VolumeTarget | None = element(tag="target", default=None)
    backing_store: VolumeBackingStore | None = element(tag="backingStore", default=None)
