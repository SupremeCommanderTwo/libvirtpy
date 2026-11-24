"""``<domaincheckpoint>``: a point in time that incremental backups start from.

It embeds the domain definition at that time, so this module uses the
``domain`` package.

See https://libvirt.org/formatcheckpoint.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml.domain import Domain

__all__ = [
    "Checkpoint",
    "CheckpointDisk",
    "CheckpointParent",
]


class CheckpointDisk(LibvirtXmlModel, tag="disk"):
    """``<disk>``: the checkpoint bitmap of one disk."""

    name: str = attr(name="name")
    checkpoint: Literal["no", "bitmap"] | None = attr(name="checkpoint", default=None)
    bitmap: str | None = attr(name="bitmap", default=None)
    size: int | None = attr(name="size", default=None, ge=0)


class CheckpointDisks(LibvirtXmlModel, tag="disks"):
    disks: list[CheckpointDisk] = element(tag="disk", default_factory=list)


class CheckpointParent(LibvirtXmlModel, tag="parent"):
    name: str = element(tag="name")


class Checkpoint(LibvirtXmlModel, tag="domaincheckpoint"):
    """``<domaincheckpoint>``: a checkpoint of a domain."""

    name: str | None = element(tag="name", default=None)
    description: str | None = element(tag="description", default=None)
    creation_time: int | None = element(tag="creationTime", default=None, ge=0)
    disks: CheckpointDisks | None = element(tag="disks", default=None)
    parent: CheckpointParent | None = element(tag="parent", default=None)
    domain: Domain | None = element(tag="domain", default=None)
