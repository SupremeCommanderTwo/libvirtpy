"""Models for domain snapshots. See https://libvirt.org/formatsnapshot.html"""

from libvirtpy.xml.snapshot.snapshot import (
    BlockSnapshotDisk,
    DomainReference,
    FileSnapshotDisk,
    InactiveDomain,
    NetworkSnapshotDisk,
    Snapshot,
    SnapshotCookie,
    SnapshotDisk,
    SnapshotDiskDriver,
    SnapshotMemory,
    SnapshotParent,
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
