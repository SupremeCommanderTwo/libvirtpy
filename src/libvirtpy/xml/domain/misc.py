"""Small domain-level elements: ``<pm>``, ``<keywrap>``, ``<perf>``, ``<resource>``,
``<idmap>`` and ``<iommufd>``.

See https://libvirt.org/formatdomain.html#power-management and the sections on
key wrap, performance monitoring events, resource partitioning and
user namespace mapping.
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import YesNo

__all__ = [
    "GidRange",
    "Idmap",
    "Iommufd",
    "Keywrap",
    "KeywrapCipher",
    "Perf",
    "PerfEvent",
    "Pm",
    "PmSuspend",
    "Resource",
    "ResourceFibrechannel",
    "UidRange",
]


class PmSuspend(LibvirtXmlModel):
    """Base of ``<suspend-to-mem>`` and ``<suspend-to-disk>``."""

    enabled: YesNo | None = attr(name="enabled", default=None)


class SuspendToMem(PmSuspend, tag="suspend-to-mem"):
    """``<suspend-to-mem>``: the S3 power state."""


class SuspendToDisk(PmSuspend, tag="suspend-to-disk"):
    """``<suspend-to-disk>``: the S4 power state."""


class Pm(LibvirtXmlModel, tag="pm"):
    """``<pm>``: guest power management."""

    suspend_to_mem: SuspendToMem | None = element(tag="suspend-to-mem", default=None)
    suspend_to_disk: SuspendToDisk | None = element(tag="suspend-to-disk", default=None)


class KeywrapCipher(LibvirtXmlModel, tag="cipher"):
    name: Literal["aes", "dea"] = attr(name="name")
    state: Literal["on", "off"] = attr(name="state")


class Keywrap(LibvirtXmlModel, tag="keywrap"):
    """``<keywrap>``: s390 cryptographic key wrapping."""

    ciphers: list[KeywrapCipher] = element(tag="cipher", default_factory=list)


class PerfEvent(LibvirtXmlModel, tag="event"):
    name: str = attr(name="name", description="e.g. ``cmt`` or ``cpu_cycles``.")
    enabled: YesNo = attr(name="enabled")


class Perf(LibvirtXmlModel, tag="perf"):
    """``<perf>``: performance monitoring events. Since 2.0.0."""

    events: list[PerfEvent] = element(tag="event", default_factory=list)


class ResourceFibrechannel(LibvirtXmlModel, tag="fibrechannel"):
    appid: str = attr(name="appid", pattern=r"^[ -~]{1,128}$")


class Resource(LibvirtXmlModel, tag="resource"):
    """``<resource>``: the cgroup partition the guest runs in."""

    partition: str | None = element(tag="partition", default=None)
    fibrechannel: ResourceFibrechannel | None = element(
        tag="fibrechannel", default=None
    )


class IdRange(LibvirtXmlModel):
    start: int = attr(name="start", ge=0)
    target: int = attr(name="target", ge=0)
    count: int = attr(name="count", ge=0)


class UidRange(IdRange, tag="uid"):
    """``<uid>``: a range of user IDs of the container."""


class GidRange(IdRange, tag="gid"):
    """``<gid>``: a range of group IDs of the container."""


class Idmap(LibvirtXmlModel, tag="idmap"):
    """``<idmap>``: user and group ID mapping of an LXC container."""

    uids: list[UidRange] = element(tag="uid", default_factory=list)
    gids: list[GidRange] = element(tag="gid", default_factory=list)


class Iommufd(LibvirtXmlModel, tag="iommufd"):
    """``<iommufd>``: use the iommufd backend for passthrough devices."""

    enabled: YesNo = attr(name="enabled")
    fdgroup: str | None = attr(name="fdgroup", default=None)
