"""``<domainbackup>``: a request to back up a running domain.

``mode='push'`` writes the backup to a ``<target>`` of each disk; ``mode='pull'``
serves it over NBD from ``<server>`` with a ``<scratch>`` file per disk.

See https://libvirt.org/formatbackup.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.storage import DeviceSeclabel, StorageEncryption
from libvirtpy.xml._types import YesNo

__all__ = [
    "Backup",
    "BackupDisk",
    "BackupDiskDriver",
    "BackupLocation",
    "BackupServer",
]


class BackupLocation(LibvirtXmlModel):
    """Base of ``<target>`` and ``<scratch>``: a file or a block device."""

    file: str | None = attr(name="file", default=None)
    dev: str | None = attr(name="dev", default=None)
    seclabels: list[DeviceSeclabel] = element(tag="seclabel", default_factory=list)
    encryption: StorageEncryption | None = element(tag="encryption", default=None)


class BackupTarget(BackupLocation, tag="target"):
    """``<target>``: where a push backup of the disk is written."""


class BackupScratch(BackupLocation, tag="scratch"):
    """``<scratch>``: the scratch image of a pull backup."""


class BackupDiskDriver(LibvirtXmlModel, tag="driver"):
    type: str = attr(name="type", description="Image format, e.g. ``qcow2``.")


class BackupDisk(LibvirtXmlModel, tag="disk"):
    """``<disk>``: what to do with one disk of the domain."""

    name: str = attr(name="name", description="Target of the disk, e.g. ``vda``.")
    # The daemon adds ``index`` to a running job; libvirt's schema does not list it.
    index: int | None = attr(name="index", default=None, ge=0)
    backup: YesNo | None = attr(name="backup", default=None)
    backupmode: Literal["full", "incremental"] | None = attr(
        name="backupmode", default=None
    )
    incremental: str | None = attr(name="incremental", default=None)
    exportname: str | None = attr(name="exportname", default=None)
    exportbitmap: str | None = attr(name="exportbitmap", default=None)
    type: Literal["file", "block"] | None = attr(name="type", default=None)
    target: BackupTarget | None = element(tag="target", default=None)
    scratch: BackupScratch | None = element(tag="scratch", default=None)
    driver: BackupDiskDriver | None = element(tag="driver", default=None)


class BackupServer(LibvirtXmlModel, tag="server"):
    """``<server>``: the NBD server of a pull backup."""

    tls: YesNo | None = attr(name="tls", default=None)
    transport: Literal["tcp", "unix", "fd"] | None = attr(
        name="transport", default=None
    )
    name: str | None = attr(name="name", default=None)
    port: int | None = attr(name="port", default=None, ge=0)
    socket: str | None = attr(name="socket", default=None)
    fdgroup: str | None = attr(name="fdgroup", default=None)


class BackupDisks(LibvirtXmlModel, tag="disks"):
    disks: list[BackupDisk] = element(tag="disk", default_factory=list)


class Backup(LibvirtXmlModel, tag="domainbackup"):
    """``<domainbackup>``: the parameters of one backup job."""

    mode: Literal["push", "pull"] | None = attr(name="mode", default=None)
    incremental: str | None = element(tag="incremental", default=None)
    server: BackupServer | None = element(tag="server", default=None)
    disks: BackupDisks | None = element(tag="disks", default=None)
