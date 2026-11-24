"""``<memory>``, ``<currentMemory>`` and ``<maxMemory>``.

See https://libvirt.org/formatdomain.html#memory-allocation
"""

from typing import Literal

from pydantic import Field
from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import (
    OnOff,
    PresenceFlag,
    ScaledInteger,
    SizeUnit,
    size_to_bytes,
)

__all__ = [
    "CurrentMemory",
    "HardLimit",
    "HugePage",
    "HugePages",
    "MaxMemory",
    "MemTune",
    "Memory",
    "MemoryAccess",
    "MemoryAllocation",
    "MemoryBacking",
    "MemorySource",
    "MinGuarantee",
    "SoftLimit",
    "SwapHardLimit",
]

# libvirt reads a size without ``unit`` as KiB.
_DEFAULT_UNIT = "KiB"


class Memory(LibvirtXmlModel, tag="memory"):
    """``<memory>``: the maximum memory allocation at boot."""

    value: int = Field(ge=0, description="Element text: the amount, in ``unit``.")
    unit: SizeUnit | None = attr(name="unit", default=None)
    dump_core: OnOff | None = attr(
        name="dumpCore",
        default=None,
        description="Include guest memory in core dumps. Since 0.10.2.",
    )

    def to_bytes(self) -> int:
        """Return the amount in bytes (a missing ``unit`` means KiB)."""
        return size_to_bytes(self.value, self.unit or _DEFAULT_UNIT)


class CurrentMemory(LibvirtXmlModel, tag="currentMemory"):
    """``<currentMemory>``: the actual allocation, may be below ``<memory>``."""

    value: int = Field(ge=0, description="Element text: the amount, in ``unit``.")
    unit: SizeUnit | None = attr(name="unit", default=None)

    def to_bytes(self) -> int:
        """Return the amount in bytes (a missing ``unit`` means KiB)."""
        return size_to_bytes(self.value, self.unit or _DEFAULT_UNIT)


class MaxMemory(LibvirtXmlModel, tag="maxMemory"):
    """``<maxMemory>``: the run time maximum for memory hotplug. Since 1.2.14."""

    value: int = Field(ge=0, description="Element text: the amount, in ``unit``.")
    unit: SizeUnit | None = attr(name="unit", default=None)
    slots: int | None = attr(
        name="slots", default=None, description="Number of hotplug slots."
    )

    def to_bytes(self) -> int:
        """Return the amount in bytes (a missing ``unit`` means KiB)."""
        return size_to_bytes(self.value, self.unit or _DEFAULT_UNIT)


class HugePage(LibvirtXmlModel, tag="page"):
    """``<page>``: a huge page size, optionally limited to some NUMA nodes."""

    size: int = attr(name="size", ge=0)
    unit: SizeUnit | None = attr(name="unit", default=None)
    nodeset: str | None = attr(name="nodeset", default=None)


class HugePages(LibvirtXmlModel, tag="hugepages"):
    """``<hugepages>``: back the guest memory with huge pages."""

    pages: list[HugePage] = element(tag="page", default_factory=list)


class MemorySource(LibvirtXmlModel, tag="source"):
    """``<source>``: how the guest memory is allocated. Since 4.10.0."""

    type: Literal["file", "anonymous", "memfd"] = attr(name="type")


class MemoryAccess(LibvirtXmlModel, tag="access"):
    """``<access>``: whether the memory is shared with other processes."""

    mode: Literal["shared", "private"] = attr(name="mode")


class MemoryAllocation(LibvirtXmlModel, tag="allocation"):
    """``<allocation>``: when and how the memory is allocated. Since 8.2.0."""

    mode: Literal["immediate", "ondemand"] | None = attr(name="mode", default=None)
    threads: int | None = attr(name="threads", default=None, ge=0)


class MemoryBacking(LibvirtXmlModel, tag="memoryBacking"):
    """``<memoryBacking>``: how the host backs the guest memory."""

    hugepages: HugePages | None = element(tag="hugepages", default=None)
    nosharepages: PresenceFlag | None = element(tag="nosharepages", default=None)
    locked: PresenceFlag | None = element(tag="locked", default=None)
    source: MemorySource | None = element(tag="source", default=None)
    access: MemoryAccess | None = element(tag="access", default=None)
    allocation: MemoryAllocation | None = element(tag="allocation", default=None)
    discard: PresenceFlag | None = element(tag="discard", default=None)


class HardLimit(ScaledInteger, tag="hard_limit"):
    """``<hard_limit>``: the maximum memory the guest may use."""


class SoftLimit(ScaledInteger, tag="soft_limit"):
    """``<soft_limit>``: the memory limit enforced under contention."""


class MinGuarantee(ScaledInteger, tag="min_guarantee"):
    """``<min_guarantee>``: the guaranteed memory (Xen)."""


class SwapHardLimit(ScaledInteger, tag="swap_hard_limit"):
    """``<swap_hard_limit>``: the maximum of memory plus swap."""


class MemTune(LibvirtXmlModel, tag="memtune"):
    """``<memtune>``: memory limits of the guest process."""

    hard_limit: HardLimit | None = element(tag="hard_limit", default=None)
    soft_limit: SoftLimit | None = element(tag="soft_limit", default=None)
    min_guarantee: MinGuarantee | None = element(tag="min_guarantee", default=None)
    swap_hard_limit: SwapHardLimit | None = element(tag="swap_hard_limit", default=None)
