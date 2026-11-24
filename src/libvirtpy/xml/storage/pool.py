"""``<pool>``: a storage pool.

All pool types (``dir``, ``fs``, ``netfs``, ``logical``, ``disk``, ``iscsi``,
``rbd``, ...) share one ``Pool`` model: they differ by which optional children
of ``<source>`` they use (hosts for network pools, devices for disk pools, ...),
and libvirt, not the model, checks which combinations are valid.

See https://libvirt.org/formatstorage.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.storage import (
    Allocation,
    Capacity,
    Permissions,
    ScsiAdapter,
)
from libvirtpy.xml._types import ScaledInteger, Uuid, YesNo

__all__ = [
    "FS_NAMESPACE",
    "RBD_NAMESPACE",
    "Pool",
    "PoolAuth",
    "PoolAuthSecret",
    "PoolAvailable",
    "PoolDevice",
    "PoolDir",
    "PoolFeatures",
    "PoolFormat",
    "PoolHost",
    "PoolSource",
    "PoolTarget",
    "PoolType",
]

FS_NAMESPACE = "http://libvirt.org/schemas/storagepool/fs/1.0"
RBD_NAMESPACE = "http://libvirt.org/schemas/storagepool/rbd/1.0"

PoolType = Literal[
    "dir",
    "fs",
    "netfs",
    "logical",
    "disk",
    "iscsi",
    "iscsi-direct",
    "scsi",
    "mpath",
    "rbd",
    "sheepdog",
    "gluster",
    "zfs",
    "vstorage",
]


class PoolAvailable(ScaledInteger, tag="available"):
    """``<available>``: the free space of the pool."""


class PoolCowState(LibvirtXmlModel, tag="cow"):
    state: YesNo = attr(name="state")


class PoolFeatures(LibvirtXmlModel, tag="features"):
    """``<features>``: file system features of the pool."""

    cow: PoolCowState | None = element(tag="cow", default=None)


class FreeExtent(LibvirtXmlModel, tag="freeExtent"):
    start: int = attr(name="start", ge=0)
    end: int = attr(name="end", ge=0)


class PoolDevice(LibvirtXmlModel, tag="device"):
    """``<device>``: a device of a disk, fs or logical pool."""

    path: str = attr(name="path")
    part_separator: YesNo | None = attr(name="part_separator", default=None)
    free_extents: list[FreeExtent] = element(tag="freeExtent", default_factory=list)


class PoolHost(LibvirtXmlModel, tag="host"):
    name: str = attr(name="name")
    port: int | None = attr(name="port", default=None, ge=0, le=65535)


class PoolDir(LibvirtXmlModel, tag="dir"):
    path: str = attr(name="path")


class PoolVendor(LibvirtXmlModel, tag="vendor"):
    name: str | None = attr(name="name", default=None)


class PoolProduct(LibvirtXmlModel, tag="product"):
    name: str | None = attr(name="name", default=None)


class PoolFormat(LibvirtXmlModel, tag="format"):
    """``<format>``: the file system or partition table type."""

    type: str = attr(name="type", description="e.g. ``ext4``, ``nfs``, ``gpt``.")
    vendor: PoolVendor | None = element(tag="vendor", default=None)
    product: PoolProduct | None = element(tag="product", default=None)


class PoolProtocol(LibvirtXmlModel, tag="protocol"):
    ver: str | None = attr(name="ver", default=None)


class PoolAuthSecret(LibvirtXmlModel, tag="secret"):
    """``<secret>`` of a pool: a libvirt secret by ``uuid`` or ``usage``."""

    uuid: Uuid | None = attr(name="uuid", default=None)
    usage: str | None = attr(name="usage", default=None)


class PoolAuth(LibvirtXmlModel, tag="auth"):
    """``<auth>``: credentials for a network pool."""

    type: Literal["chap", "ceph"] = attr(name="type")
    username: str = attr(name="username")
    secret: PoolAuthSecret = element(tag="secret")


class PoolInitiatorIqn(LibvirtXmlModel, tag="iqn"):
    name: str = attr(name="name")


class PoolInitiator(LibvirtXmlModel, tag="initiator"):
    iqn: PoolInitiatorIqn = element(tag="iqn")


class PoolSource(LibvirtXmlModel, tag="source"):
    """``<source>``: where the pool's storage comes from."""

    hosts: list[PoolHost] = element(tag="host", default_factory=list)
    devices: list[PoolDevice] = element(tag="device", default_factory=list)
    dir: PoolDir | None = element(tag="dir", default=None)
    names: list[str] = element(tag="name", default_factory=list)
    format: PoolFormat | None = element(tag="format", default=None)
    protocol: PoolProtocol | None = element(tag="protocol", default=None)
    adapter: ScsiAdapter | None = element(tag="adapter", default=None)
    auth: PoolAuth | None = element(tag="auth", default=None)
    initiator: PoolInitiator | None = element(tag="initiator", default=None)
    vendor: PoolVendor | None = element(tag="vendor", default=None)
    product: PoolProduct | None = element(tag="product", default=None)


class PoolTarget(LibvirtXmlModel, tag="target"):
    """``<target>``: where the pool is mapped in the host file system."""

    path: str | None = element(tag="path", default=None)
    permissions: Permissions | None = element(tag="permissions", default=None)


class RefreshVolume(LibvirtXmlModel, tag="volume"):
    allocation: Literal["default", "capacity"] | None = attr(
        name="allocation", default=None
    )


class PoolRefresh(LibvirtXmlModel, tag="refresh"):
    """``<refresh>``: how the pool refreshes its volume list. Since 6.7.0."""

    volume: RefreshVolume | None = element(tag="volume", default=None)


class MountOption(LibvirtXmlModel, tag="option", ns="fs", nsmap={"fs": FS_NAMESPACE}):
    name: str = attr(name="name")


class MountOptions(
    LibvirtXmlModel, tag="mount_opts", ns="fs", nsmap={"fs": FS_NAMESPACE}
):
    """``<fs:mount_opts>``: extra mount options of an ``fs`` or ``netfs`` pool."""

    options: list[MountOption] = element(tag="option", default_factory=list)


class RbdOption(LibvirtXmlModel, tag="option", ns="rbd", nsmap={"rbd": RBD_NAMESPACE}):
    name: str = attr(name="name")
    value: str = attr(name="value")


class RbdConfigOptions(
    LibvirtXmlModel, tag="config_opts", ns="rbd", nsmap={"rbd": RBD_NAMESPACE}
):
    """``<rbd:config_opts>``: extra librbd settings."""

    options: list[RbdOption] = element(tag="option", default_factory=list)


class Pool(LibvirtXmlModel, tag="pool"):
    """``<pool>``: a storage pool."""

    type: PoolType = attr(name="type")
    name: str | None = element(tag="name", default=None)
    uuid: Uuid | None = element(tag="uuid", default=None)
    capacity: Capacity | None = element(tag="capacity", default=None)
    allocation: Allocation | None = element(tag="allocation", default=None)
    available: PoolAvailable | None = element(tag="available", default=None)
    features: PoolFeatures | None = element(tag="features", default=None)
    source: PoolSource | None = element(tag="source", default=None)
    target: PoolTarget | None = element(tag="target", default=None)
    refresh: PoolRefresh | None = element(tag="refresh", default=None)
    mount_options: MountOptions | None = element(
        tag="mount_opts", ns="fs", nsmap={"fs": FS_NAMESPACE}, default=None
    )
    rbd_config_options: RbdConfigOptions | None = element(
        tag="config_opts", ns="rbd", nsmap={"rbd": RBD_NAMESPACE}, default=None
    )
