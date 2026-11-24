"""``<filesystem>``: directories and images shared with the guest.

One class per ``type``; ``Filesystem`` is their plain union. A missing ``type``
means ``mount``.

See https://libvirt.org/formatdomain.html#filesystems
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff, PresenceFlag, ScaledInteger
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import (
    Alias,
    DeviceAcpi,
    DeviceBoot,
    VirtioDriverOptions,
)

__all__ = [
    "BindFilesystem",
    "BlockFilesystem",
    "FileFilesystem",
    "Filesystem",
    "FilesystemBinary",
    "FilesystemDriver",
    "MountFilesystem",
    "RamFilesystem",
    "TemplateFilesystem",
]


class FilesystemDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>``: how the host serves the filesystem."""

    type: (
        Literal["path", "handle", "loop", "nbd", "ploop", "virtiofs", "mtp"] | None
    ) = attr(name="type", default=None)
    format: str | None = attr(name="format", default=None)
    wrpolicy: Literal["immediate"] | None = attr(name="wrpolicy", default=None)
    queue: int | None = attr(name="queue", default=None, ge=0)


class FilesystemTarget(LibvirtXmlModel, tag="target"):
    dir: str = attr(name="dir", description="Mount tag or directory in the guest.")


class HardLimit(ScaledInteger, tag="space_hard_limit"):
    """``<space_hard_limit>``: maximum space of an LXC filesystem."""


class SoftLimit(ScaledInteger, tag="space_soft_limit"):
    """``<space_soft_limit>``: soft space limit of an LXC filesystem."""


class IdmapRange(LibvirtXmlModel):
    start: int = attr(name="start", ge=0)
    target: int = attr(name="target", ge=0)
    count: int = attr(name="count", ge=0)


class UidRange(IdmapRange, tag="uid"):
    """``<uid>``: a range of user IDs."""


class GidRange(IdmapRange, tag="gid"):
    """``<gid>``: a range of group IDs."""


class FilesystemIdmap(LibvirtXmlModel, tag="idmap"):
    """``<idmap>``: user and group ID mapping."""

    uids: list[UidRange] = element(tag="uid", default_factory=list)
    gids: list[GidRange] = element(tag="gid", default_factory=list)


class BinaryCache(LibvirtXmlModel, tag="cache"):
    mode: Literal["none", "always"] | None = attr(name="mode", default=None)


class BinarySandbox(LibvirtXmlModel, tag="sandbox"):
    mode: Literal["namespace", "chroot"] | None = attr(name="mode", default=None)


class BinaryLock(LibvirtXmlModel, tag="lock"):
    posix: OnOff | None = attr(name="posix", default=None)
    flock: OnOff | None = attr(name="flock", default=None)


class BinaryThreadPool(LibvirtXmlModel, tag="thread_pool"):
    size: int = attr(name="size")


class BinaryOpenfiles(LibvirtXmlModel, tag="openfiles"):
    max: int = attr(name="max", ge=1)


class FilesystemBinary(LibvirtXmlModel, tag="binary"):
    """``<binary>``: the virtiofsd helper and its options."""

    path: str | None = attr(name="path", default=None)
    xattr: OnOff | None = attr(name="xattr", default=None)
    cache: BinaryCache | None = element(tag="cache", default=None)
    sandbox: BinarySandbox | None = element(tag="sandbox", default=None)
    lock: BinaryLock | None = element(tag="lock", default=None)
    thread_pool: BinaryThreadPool | None = element(tag="thread_pool", default=None)
    openfiles: BinaryOpenfiles | None = element(tag="openfiles", default=None)


class _FilesystemBase(LibvirtXmlModel, tag="filesystem"):
    """Fields every filesystem type has."""

    model: (
        Literal["virtio", "virtio-transitional", "virtio-non-transitional"] | None
    ) = attr(name="model", default=None)
    accessmode: Literal["passthrough", "mapped", "squash"] | None = attr(
        name="accessmode", default=None
    )
    multidevs: Literal["default", "remap", "forbid", "warn"] | None = attr(
        name="multidevs", default=None
    )
    fmode: str | None = attr(name="fmode", default=None)
    dmode: str | None = attr(name="dmode", default=None)
    driver: FilesystemDriver | None = element(tag="driver", default=None)
    target: FilesystemTarget | None = element(tag="target", default=None)
    readonly: PresenceFlag | None = element(tag="readonly", default=None)
    space_hard_limit: HardLimit | None = element(tag="space_hard_limit", default=None)
    space_soft_limit: SoftLimit | None = element(tag="space_soft_limit", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
    boot: DeviceBoot | None = element(tag="boot", default=None)


class FileSource(LibvirtXmlModel, tag="source"):
    file: str = attr(name="file")


class FileFilesystem(_FilesystemBase, tag="filesystem"):
    type: Literal["file"] = attr(name="type")
    source: FileSource | None = element(tag="source", default=None)


class BlockSource(LibvirtXmlModel, tag="source"):
    dev: str = attr(name="dev")


class BlockFilesystem(_FilesystemBase, tag="filesystem"):
    type: Literal["block"] = attr(name="type")
    source: BlockSource | None = element(tag="source", default=None)


class MountSource(LibvirtXmlModel, tag="source"):
    dir: str | None = attr(name="dir", default=None)
    socket: str | None = attr(name="socket", default=None)


class MountFilesystem(_FilesystemBase, tag="filesystem"):
    """``type='mount'``, also the default when ``type`` is missing."""

    type: Literal["mount"] | None = attr(name="type", default=None)
    source: MountSource | None = element(tag="source", default=None)
    binary: FilesystemBinary | None = element(tag="binary", default=None)
    idmap: FilesystemIdmap | None = element(tag="idmap", default=None)


class BindSource(LibvirtXmlModel, tag="source"):
    dir: str = attr(name="dir")


class BindFilesystem(_FilesystemBase, tag="filesystem"):
    type: Literal["bind"] = attr(name="type")
    source: BindSource | None = element(tag="source", default=None)


class TemplateSource(LibvirtXmlModel, tag="source"):
    name: str = attr(name="name")


class TemplateFilesystem(_FilesystemBase, tag="filesystem"):
    type: Literal["template"] = attr(name="type")
    source: TemplateSource | None = element(tag="source", default=None)


class RamSource(LibvirtXmlModel, tag="source"):
    usage: int = attr(name="usage", ge=0)
    units: str | None = attr(name="units", default=None)


class RamFilesystem(_FilesystemBase, tag="filesystem"):
    type: Literal["ram"] = attr(name="type")
    source: RamSource | None = element(tag="source", default=None)


Filesystem = (
    MountFilesystem
    | FileFilesystem
    | BlockFilesystem
    | BindFilesystem
    | TemplateFilesystem
    | RamFilesystem
)
"""Any ``<filesystem>``; the variant is chosen by its ``type`` attribute."""
