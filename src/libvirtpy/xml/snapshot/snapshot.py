"""``<domainsnapshot>``: a snapshot of a domain.

A snapshot embeds the domain definition at that time and describes its disks
with the same storage sources as a ``<disk>``, so this module uses the
``domain`` package.

See https://libvirt.org/formatsnapshot.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.metadata import RawChildren
from libvirtpy.xml._types import PresenceFlag, Uuid
from libvirtpy.xml.domain import Domain
from libvirtpy.xml.domain.storage_source import (
    BlockStorage,
    FileStorage,
    MetadataCache,
    NetworkStorage,
)

__all__ = [
    "BlockSnapshotDisk",
    "DomainReference",
    "FileSnapshotDisk",
    "InactiveDomain",
    "NetworkSnapshotDisk",
    "Snapshot",
    "SnapshotCookie",
    "SnapshotDisk",
    "SnapshotDiskDriver",
    "SnapshotMemory",
    "SnapshotParent",
]


class DomainReference(LibvirtXmlModel, tag="domain"):
    """``<domain>`` that only names the domain by its UUID."""

    uuid: Uuid = element(tag="uuid")


class InactiveDomain(Domain, tag="inactiveDomain"):
    """``<inactiveDomain>``: the persistent definition, if it differs from the live."""


class SnapshotCookie(RawChildren, tag="cookie"):
    """``<cookie>``: hypervisor private data, kept as XML strings."""


class SnapshotMemory(LibvirtXmlModel, tag="memory"):
    """``<memory>``: whether and where the guest memory is saved."""

    snapshot: Literal["no", "internal", "external"] = attr(name="snapshot")
    file: str | None = attr(name="file", default=None)


class SnapshotParent(LibvirtXmlModel, tag="parent"):
    name: str = element(tag="name")


class SnapshotDiskDriver(LibvirtXmlModel, tag="driver"):
    """``<driver>``: the image format of an external snapshot file."""

    type: str | None = attr(name="type", default=None)
    metadata_cache: MetadataCache | None = element(tag="metadata_cache", default=None)


class _SnapshotDiskBase(LibvirtXmlModel):
    """Fields every snapshot disk has, whatever its ``type``."""

    name: str = attr(
        name="name", description="Target of the disk (``vda``) or its source path."
    )
    snapshot: Literal["no", "internal", "external", "manual"] | None = attr(
        name="snapshot", default=None
    )
    driver: SnapshotDiskDriver | None = element(tag="driver", default=None)
    snapshot_delete_in_progress: PresenceFlag | None = element(
        tag="snapshotDeleteInProgress", default=None
    )


class FileSnapshotDisk(_SnapshotDiskBase, FileStorage, tag="disk"):
    """A snapshot disk that is a file; also one without ``type``."""


class BlockSnapshotDisk(_SnapshotDiskBase, BlockStorage, tag="disk"):
    """A snapshot disk of ``type='block'``."""


class NetworkSnapshotDisk(_SnapshotDiskBase, NetworkStorage, tag="disk"):
    """A snapshot disk of ``type='network'``."""


SnapshotDisk = FileSnapshotDisk | BlockSnapshotDisk | NetworkSnapshotDisk
"""Any snapshot ``<disk>``; the variant is chosen by its ``type`` attribute."""


class SnapshotDisks(LibvirtXmlModel, tag="disks"):
    disks: list[SnapshotDisk] = element(tag="disk", default_factory=list)


class RevertDisks(LibvirtXmlModel, tag="revertDisks"):
    disks: list[SnapshotDisk] = element(tag="disk", default_factory=list)


class Snapshot(LibvirtXmlModel, tag="domainsnapshot"):
    """``<domainsnapshot>``: a snapshot of a domain."""

    name: str | None = element(tag="name", default=None)
    description: str | None = element(tag="description", default=None)
    state: (
        Literal[
            "running",
            "blocked",
            "paused",
            "shutdown",
            "shutoff",
            "crashed",
            "disk-snapshot",
        ]
        | None
    ) = element(tag="state", default=None)
    creation_time: str | None = element(tag="creationTime", default=None)
    parent: SnapshotParent | None = element(tag="parent", default=None)
    memory: SnapshotMemory | None = element(tag="memory", default=None)
    disks: SnapshotDisks | None = element(tag="disks", default=None)
    revert_disks: RevertDisks | None = element(tag="revertDisks", default=None)
    domain: Domain | DomainReference | None = element(tag="domain", default=None)
    inactive_domain: InactiveDomain | None = element(tag="inactiveDomain", default=None)
    active: str | None = element(tag="active", default=None)
    cookie: SnapshotCookie | None = element(tag="cookie", default=None)
