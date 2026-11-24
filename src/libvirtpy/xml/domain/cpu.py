"""``<vcpu>`` and ``<cpu>`` (``<cputune>`` will follow).

See https://libvirt.org/formatdomain.html#cpu-allocation and
https://libvirt.org/formatdomain.html#cpu-model-and-topology
"""

from typing import Literal

from pydantic import Field
from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff, OptionalText, SizeUnit, YesNo
from libvirtpy.xml.domain.numa import Numa

__all__ = [
    "CacheTune",
    "CacheTuneCache",
    "CacheTuneMonitor",
    "Cpu",
    "CpuCache",
    "CpuFeature",
    "CpuModel",
    "CpuTopology",
    "Cputune",
    "EmulatorPin",
    "EmulatorSched",
    "EnergyTune",
    "EnergyTuneMonitor",
    "IothreadPin",
    "IothreadSched",
    "MaxPhysAddr",
    "MemoryTune",
    "MemoryTuneMonitor",
    "MemoryTuneNode",
    "Vcpu",
    "VcpuInfo",
    "VcpuPin",
    "VcpuSched",
    "Vcpus",
]


class Vcpu(LibvirtXmlModel, tag="vcpu"):
    """``<vcpu>``: the maximum number of virtual CPUs."""

    value: int = Field(ge=1, description="Element text: maximum vCPU count.")
    placement: Literal["static", "auto"] | None = attr(name="placement", default=None)
    cpuset: str | None = attr(
        name="cpuset",
        default=None,
        description="Host CPUs the vCPUs may run on, e.g. ``1-4,^3,6``.",
    )
    current: int | None = attr(
        name="current",
        default=None,
        description="vCPUs enabled at boot. Since 0.8.5.",
    )


class CpuModel(LibvirtXmlModel, tag="model"):
    """``<model>``: the CPU model the guest sees."""

    value: OptionalText = Field(
        default=None, description="Element text: model name, e.g. ``Skylake-Client``."
    )
    fallback: Literal["allow", "forbid"] | None = attr(name="fallback", default=None)
    vendor_id: str | None = attr(
        name="vendor_id",
        default=None,
        pattern=r"^[^,]{12}$",
        description="CPUID vendor string, exactly 12 characters. Since 0.10.0.",
    )


class CpuTopology(LibvirtXmlModel, tag="topology"):
    """``<topology>``: how vCPUs are split into sockets, cores and threads."""

    sockets: int = attr(name="sockets", ge=1)
    dies: int | None = attr(name="dies", default=None, ge=1)
    clusters: int | None = attr(name="clusters", default=None, ge=1)
    cores: int = attr(name="cores", ge=1)
    threads: int = attr(name="threads", ge=1)


class CpuFeature(LibvirtXmlModel, tag="feature"):
    """``<feature>``: a CPU feature and how strictly to apply it."""

    policy: Literal["force", "require", "optional", "disable", "forbid"] = attr(
        name="policy"
    )
    name: str = attr(name="name")


class CpuCache(LibvirtXmlModel, tag="cache"):
    """``<cache>`` in ``<cpu>``: the CPU cache the guest sees. Since 3.3.0."""

    level: int | None = attr(name="level", default=None, ge=1, le=3)
    mode: Literal["emulate", "passthrough", "disable"] = attr(name="mode")


class MaxPhysAddr(LibvirtXmlModel, tag="maxphysaddr"):
    """``<maxphysaddr>``: the guest's physical address size. Since 8.7.0."""

    mode: Literal["emulate", "passthrough"] = attr(name="mode")
    bits: int | None = attr(name="bits", default=None, ge=0)
    limit: int | None = attr(name="limit", default=None, ge=0)


class Cpu(LibvirtXmlModel, tag="cpu"):
    """``<cpu>``: CPU model, features, topology and NUMA layout."""

    mode: Literal["custom", "host-model", "host-passthrough", "maximum"] | None = attr(
        name="mode", default=None
    )
    match: Literal["minimum", "exact", "strict"] | None = attr(
        name="match", default=None
    )
    check: Literal["none", "partial", "full"] | None = attr(name="check", default=None)
    deprecated_features: OnOff | None = attr(name="deprecated_features", default=None)
    migratable: OnOff | None = attr(name="migratable", default=None)
    model: CpuModel | None = element(tag="model", default=None)
    vendor: str | None = element(tag="vendor", default=None)
    topology: CpuTopology | None = element(tag="topology", default=None)
    features: list[CpuFeature] = element(tag="feature", default_factory=list)
    numa: Numa | None = element(tag="numa", default=None)
    cache: CpuCache | None = element(tag="cache", default=None)
    max_phys_addr: MaxPhysAddr | None = element(tag="maxphysaddr", default=None)


class VcpuInfo(LibvirtXmlModel, tag="vcpu"):
    """``<vcpu>`` inside ``<vcpus>``: the state of one virtual CPU."""

    id: int = attr(name="id", ge=0)
    enabled: YesNo = attr(name="enabled")
    hotpluggable: YesNo | None = attr(name="hotpluggable", default=None)
    order: int | None = attr(name="order", default=None, ge=0)


class Vcpus(LibvirtXmlModel, tag="vcpus"):
    """``<vcpus>``: per-vCPU hotplug state."""

    vcpus: list[VcpuInfo] = element(tag="vcpu", default_factory=list)


class VcpuPin(LibvirtXmlModel, tag="vcpupin"):
    """``<vcpupin>``: pin one vCPU to host CPUs."""

    vcpu: int = attr(name="vcpu", ge=0)
    cpuset: str = attr(name="cpuset")


class EmulatorPin(LibvirtXmlModel, tag="emulatorpin"):
    """``<emulatorpin>``: pin the emulator threads to host CPUs."""

    cpuset: str = attr(name="cpuset")


class IothreadPin(LibvirtXmlModel, tag="iothreadpin"):
    """``<iothreadpin>``: pin one I/O thread to host CPUs."""

    iothread: int = attr(name="iothread", ge=0)
    cpuset: str = attr(name="cpuset")


Scheduler = Literal["batch", "idle", "fifo", "rr"]


class VcpuSched(LibvirtXmlModel, tag="vcpusched"):
    """``<vcpusched>``: the scheduler policy of some vCPUs."""

    vcpus: str | None = attr(name="vcpus", default=None)
    scheduler: Scheduler = attr(name="scheduler")
    priority: int | None = attr(name="priority", default=None, ge=0, le=65535)


class IothreadSched(LibvirtXmlModel, tag="iothreadsched"):
    """``<iothreadsched>``: the scheduler policy of some I/O threads."""

    iothreads: str | None = attr(name="iothreads", default=None)
    scheduler: Scheduler = attr(name="scheduler")
    priority: int | None = attr(name="priority", default=None, ge=0, le=65535)


class EmulatorSched(LibvirtXmlModel, tag="emulatorsched"):
    """``<emulatorsched>``: the scheduler policy of the emulator threads."""

    scheduler: Scheduler = attr(name="scheduler")
    priority: int | None = attr(name="priority", default=None, ge=0, le=65535)


class CacheTuneCache(LibvirtXmlModel, tag="cache"):
    id: int = attr(name="id", ge=0)
    level: int = attr(name="level", ge=0)
    type: Literal["both", "code", "data"] = attr(name="type")
    size: int = attr(name="size", ge=0)
    unit: SizeUnit | None = attr(name="unit", default=None)


class CacheTuneMonitor(LibvirtXmlModel, tag="monitor"):
    level: int = attr(name="level", ge=0)
    vcpus: str | None = attr(name="vcpus", default=None)


class CacheTune(LibvirtXmlModel, tag="cachetune"):
    """``<cachetune>``: CPU cache allocation (Intel CAT). Since 4.1.0."""

    vcpus: str | None = attr(name="vcpus", default=None)
    id: str | None = attr(name="id", default=None)
    caches: list[CacheTuneCache] = element(tag="cache", default_factory=list)
    monitors: list[CacheTuneMonitor] = element(tag="monitor", default_factory=list)


class MemoryTuneNode(LibvirtXmlModel, tag="node"):
    id: int = attr(name="id", ge=0)
    bandwidth: int = attr(name="bandwidth", ge=0)


class MemoryTuneMonitor(LibvirtXmlModel, tag="monitor"):
    vcpus: str | None = attr(name="vcpus", default=None)


class MemoryTune(LibvirtXmlModel, tag="memorytune"):
    """``<memorytune>``: memory bandwidth allocation. Since 4.7.0."""

    vcpus: str | None = attr(name="vcpus", default=None)
    nodes: list[MemoryTuneNode] = element(tag="node", default_factory=list)
    monitors: list[MemoryTuneMonitor] = element(tag="monitor", default_factory=list)


class EnergyTuneMonitor(LibvirtXmlModel, tag="monitor"):
    vcpus: str | None = attr(name="vcpus", default=None)


class EnergyTune(LibvirtXmlModel, tag="energytune"):
    """``<energytune>``: CPU energy monitoring."""

    vcpus: str | None = attr(name="vcpus", default=None)
    id: str | None = attr(name="id", default=None)
    monitors: list[EnergyTuneMonitor] = element(tag="monitor", default_factory=list)


class Cputune(LibvirtXmlModel, tag="cputune"):
    """``<cputune>``: CPU scheduling, pinning and resource control."""

    shares: int | None = element(tag="shares", default=None, ge=0)
    global_period: int | None = element(tag="global_period", default=None)
    global_quota: int | None = element(tag="global_quota", default=None)
    period: int | None = element(tag="period", default=None)
    quota: int | None = element(tag="quota", default=None)
    emulator_period: int | None = element(tag="emulator_period", default=None)
    emulator_quota: int | None = element(tag="emulator_quota", default=None)
    iothread_period: int | None = element(tag="iothread_period", default=None)
    iothread_quota: int | None = element(tag="iothread_quota", default=None)
    vcpupins: list[VcpuPin] = element(tag="vcpupin", default_factory=list)
    emulatorpin: EmulatorPin | None = element(tag="emulatorpin", default=None)
    iothreadpins: list[IothreadPin] = element(tag="iothreadpin", default_factory=list)
    vcpuscheds: list[VcpuSched] = element(tag="vcpusched", default_factory=list)
    iothreadscheds: list[IothreadSched] = element(
        tag="iothreadsched", default_factory=list
    )
    emulatorsched: EmulatorSched | None = element(tag="emulatorsched", default=None)
    cachetunes: list[CacheTune] = element(tag="cachetune", default_factory=list)
    memorytunes: list[MemoryTune] = element(tag="memorytune", default_factory=list)
    energytunes: list[EnergyTune] = element(tag="energytune", default_factory=list)
