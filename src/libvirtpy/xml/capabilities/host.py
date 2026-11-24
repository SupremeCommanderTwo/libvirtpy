"""``<capabilities>``: what the host and its hypervisors can do.

Read-only: libvirt generates it, you only parse it.

See https://libvirt.org/formatcaps.html
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
    Uuid,
    YesNo,
)

__all__ = [
    "Capabilities",
    "GuestArch",
    "GuestCapabilities",
    "GuestDomain",
    "HostCapabilities",
    "HostCpu",
    "HostTopology",
    "SecModel",
]


# host <cpu>


class HostCpuFeatures(LibvirtXmlModel, tag="features"):
    """``<features>``: legacy x86 feature flags."""

    pae: PresenceFlag | None = element(tag="pae", default=None)
    nonpae: PresenceFlag | None = element(tag="nonpae", default=None)
    vmx: PresenceFlag | None = element(tag="vmx", default=None)
    svm: PresenceFlag | None = element(tag="svm", default=None)


class Microcode(LibvirtXmlModel, tag="microcode"):
    version: int = attr(name="version", ge=1)


class Signature(LibvirtXmlModel, tag="signature"):
    family: int = attr(name="family", ge=1)
    model: int = attr(name="model", ge=0)
    stepping: int = attr(name="stepping", ge=0)


class Counter(LibvirtXmlModel, tag="counter"):
    name: str = attr(name="name")
    frequency: int = attr(name="frequency", ge=1)
    scaling: YesNo = attr(name="scaling")


class HostCpuTopology(LibvirtXmlModel, tag="topology"):
    sockets: int = attr(name="sockets", ge=1)
    dies: int | None = attr(name="dies", default=None, ge=1)
    clusters: int | None = attr(name="clusters", default=None, ge=1)
    cores: int = attr(name="cores", ge=1)
    threads: int = attr(name="threads", ge=1)


class HostMaxPhysAddr(LibvirtXmlModel, tag="maxphysaddr"):
    mode: Literal["emulate", "passthrough"] = attr(name="mode")
    bits: int | None = attr(name="bits", default=None, ge=0)
    limit: int | None = attr(name="limit", default=None, ge=0)


class HostCpuFeature(LibvirtXmlModel, tag="feature"):
    name: str = attr(name="name")


class HostPages(LibvirtXmlModel, tag="pages"):
    """``<pages>``: a supported page size."""

    unit: SizeUnit | None = attr(name="unit", default=None)
    size: int = attr(name="size", ge=0)


class HostCpu(LibvirtXmlModel, tag="cpu"):
    """``<cpu>``: the host CPU."""

    arch: str = element(tag="arch")
    features_legacy: HostCpuFeatures | None = element(tag="features", default=None)
    model: str | None = element(tag="model", default=None)
    vendor: str | None = element(tag="vendor", default=None)
    microcode: Microcode | None = element(tag="microcode", default=None)
    signature: Signature | None = element(tag="signature", default=None)
    counter: Counter | None = element(tag="counter", default=None)
    topology: HostCpuTopology | None = element(tag="topology", default=None)
    maxphysaddr: HostMaxPhysAddr | None = element(tag="maxphysaddr", default=None)
    features: list[HostCpuFeature] = element(tag="feature", default_factory=list)
    pages: list[HostPages] = element(tag="pages", default_factory=list)


# power, iommu, ...


class PowerManagement(LibvirtXmlModel, tag="power_management"):
    suspend_mem: PresenceFlag | None = element(tag="suspend_mem", default=None)
    suspend_disk: PresenceFlag | None = element(tag="suspend_disk", default=None)
    suspend_hybrid: PresenceFlag | None = element(tag="suspend_hybrid", default=None)


class HostIommu(LibvirtXmlModel, tag="iommu"):
    support: YesNo | None = attr(name="support", default=None)


class UriTransports(LibvirtXmlModel, tag="uri_transports"):
    transports: list[Literal["vpxmigr", "tcp", "rdma", "vzmigr"]] = element(
        tag="uri_transport", default_factory=list
    )


class MigrationFeatures(LibvirtXmlModel, tag="migration_features"):
    live: PresenceFlag | None = element(tag="live", default=None)
    uri_transports: UriTransports | None = element(tag="uri_transports", default=None)


# topology


class CellMemory(ScaledInteger, tag="memory"):
    """``<memory>``: the memory of a NUMA cell."""


class CellPages(LibvirtXmlModel, tag="pages"):
    """``<pages>``: how many pages of a size the cell has."""

    value: int = Field(ge=0, description="Element text: the number of pages.")
    unit: SizeUnit | None = attr(name="unit", default=None)
    size: int = attr(name="size", ge=0)


class CellSibling(LibvirtXmlModel, tag="sibling"):
    id: int = attr(name="id", ge=0)
    value: int = attr(name="value", ge=0)


class CellDistances(LibvirtXmlModel, tag="distances"):
    siblings: list[CellSibling] = element(tag="sibling", default_factory=list)


class CellCacheSize(LibvirtXmlModel, tag="size"):
    value: int = attr(name="value", ge=0)
    unit: SizeUnit = attr(name="unit")


class CellCacheLine(LibvirtXmlModel, tag="line"):
    value: int = attr(name="value", ge=0)
    unit: SizeUnit = attr(name="unit")


class CellCache(LibvirtXmlModel, tag="cache"):
    level: int = attr(name="level", ge=0)
    associativity: Literal["none", "direct", "full"] = attr(name="associativity")
    policy: Literal["none", "writeback", "writethrough"] = attr(name="policy")
    size: CellCacheSize = element(tag="size")
    line: CellCacheLine = element(tag="line")


class CellCpu(LibvirtXmlModel, tag="cpu"):
    id: int = attr(name="id", ge=0)
    socket_id: int | None = attr(name="socket_id", default=None, ge=0)
    die_id: int | None = attr(name="die_id", default=None, ge=0)
    cluster_id: int | None = attr(name="cluster_id", default=None, ge=0)
    core_id: int | None = attr(name="core_id", default=None, ge=0)
    siblings: str | None = attr(name="siblings", default=None)


class CellCpus(LibvirtXmlModel, tag="cpus"):
    num: int = attr(name="num", ge=0)
    cpus: list[CellCpu] = element(tag="cpu", default_factory=list)


class Cell(LibvirtXmlModel, tag="cell"):
    """``<cell>``: one NUMA node of the host."""

    id: int = attr(name="id", ge=0)
    memory: CellMemory | None = element(tag="memory", default=None)
    pages: list[CellPages] = element(tag="pages", default_factory=list)
    distances: CellDistances | None = element(tag="distances", default=None)
    caches: list[CellCache] = element(tag="cache", default_factory=list)
    cpus: CellCpus | None = element(tag="cpus", default=None)


class Cells(LibvirtXmlModel, tag="cells"):
    num: int = attr(name="num", ge=0)
    cells: list[Cell] = element(tag="cell", default_factory=list)


class InterconnectLatency(LibvirtXmlModel, tag="latency"):
    initiator: int = attr(name="initiator", ge=0)
    target: int = attr(name="target", ge=0)
    cache: int | None = attr(name="cache", default=None, ge=0)
    type: Literal["access", "read", "write"] = attr(name="type")
    value: int = attr(name="value", ge=0)


class InterconnectBandwidth(LibvirtXmlModel, tag="bandwidth"):
    initiator: int = attr(name="initiator", ge=0)
    target: int = attr(name="target", ge=0)
    cache: int | None = attr(name="cache", default=None, ge=0)
    type: Literal["access", "read", "write"] = attr(name="type")
    value: int = attr(name="value", ge=0)
    unit: SizeUnit = attr(name="unit")


class Interconnects(LibvirtXmlModel, tag="interconnects"):
    latencies: list[InterconnectLatency] = element(tag="latency", default_factory=list)
    bandwidths: list[InterconnectBandwidth] = element(
        tag="bandwidth", default_factory=list
    )


class HostTopology(LibvirtXmlModel, tag="topology"):
    """``<topology>``: the NUMA topology of the host."""

    cells: Cells = element(tag="cells")
    interconnects: Interconnects | None = element(tag="interconnects", default=None)


# cache, bandwidth


class MonitorFeature(LibvirtXmlModel, tag="feature"):
    name: str = attr(name="name")


class CacheMonitor(LibvirtXmlModel, tag="monitor"):
    """``<monitor>``: the cache/bandwidth monitoring of the CPU."""

    level: int | None = attr(name="level", default=None, ge=0)
    reuse_threshold: int | None = attr(name="reuseThreshold", default=None, ge=0)
    max_monitors: int = attr(name="maxMonitors", ge=0)
    features: list[MonitorFeature] = element(tag="feature", default_factory=list)


class BankControl(LibvirtXmlModel, tag="control"):
    granularity: int = attr(name="granularity", ge=0)
    min: int | None = attr(name="min", default=None, ge=0)
    unit: SizeUnit | None = attr(name="unit", default=None)
    type: Literal["both", "code", "data"] | None = attr(name="type", default=None)
    max_allocs: int = attr(name="maxAllocs", ge=0)


class CacheBank(LibvirtXmlModel, tag="bank"):
    id: int = attr(name="id", ge=0)
    level: int = attr(name="level", ge=0)
    type: Literal["both", "code", "data"] = attr(name="type")
    size: int = attr(name="size", ge=0)
    unit: SizeUnit = attr(name="unit")
    cpus: str = attr(name="cpus")
    controls: list[BankControl] = element(tag="control", default_factory=list)


class HostCache(LibvirtXmlModel, tag="cache"):
    banks: list[CacheBank] = element(tag="bank", default_factory=list)
    monitor: CacheMonitor | None = element(tag="monitor", default=None)


class BandwidthControl(LibvirtXmlModel, tag="control"):
    granularity: int = attr(name="granularity", ge=0)
    min: int | None = attr(name="min", default=None, ge=0)
    max_allocs: int = attr(name="maxAllocs", ge=0)


class BandwidthNode(LibvirtXmlModel, tag="node"):
    id: int = attr(name="id", ge=0)
    cpus: str = attr(name="cpus")
    controls: list[BandwidthControl] = element(tag="control", default_factory=list)


class MemoryBandwidth(LibvirtXmlModel, tag="memory_bandwidth"):
    nodes: list[BandwidthNode] = element(tag="node", default_factory=list)
    monitor: CacheMonitor | None = element(tag="monitor", default=None)


class EnergyMonitor(LibvirtXmlModel, tag="monitor"):
    max_monitors: int = attr(name="maxMonitors", ge=0)
    features: list[MonitorFeature] = element(tag="feature", default_factory=list)


class Energy(LibvirtXmlModel, tag="energy"):
    monitor: EnergyMonitor = element(tag="monitor")


class SecModelLabel(LibvirtXmlModel, tag="baselabel"):
    value: str = ""
    type: str = attr(name="type")


class SecModel(LibvirtXmlModel, tag="secmodel"):
    """``<secmodel>``: a security driver of the host."""

    model: str = element(tag="model")
    doi: str = element(tag="doi")
    baselabels: list[SecModelLabel] = element(tag="baselabel", default_factory=list)


class HostCapabilities(LibvirtXmlModel, tag="host"):
    """``<host>``: the host itself."""

    uuid: Uuid | None = element(tag="uuid", default=None)
    cpu: HostCpu = element(tag="cpu")
    power_management: PowerManagement | None = element(
        tag="power_management", default=None
    )
    iommu: HostIommu | None = element(tag="iommu", default=None)
    migration_features: MigrationFeatures | None = element(
        tag="migration_features", default=None
    )
    topology: HostTopology | None = element(tag="topology", default=None)
    cache: HostCache | None = element(tag="cache", default=None)
    memory_bandwidth: MemoryBandwidth | None = element(
        tag="memory_bandwidth", default=None
    )
    energy: Energy | None = element(tag="energy", default=None)
    secmodels: list[SecModel] = element(tag="secmodel", default_factory=list)


# guests


class Machine(LibvirtXmlModel, tag="machine"):
    """``<machine>``: a machine type."""

    value: str = ""
    canonical: str | None = attr(name="canonical", default=None)
    max_cpus: int | None = attr(name="maxCpus", default=None, ge=0)
    deprecated: YesNo | None = attr(name="deprecated", default=None)


class GuestDomain(LibvirtXmlModel, tag="domain"):
    """``<domain>``: a hypervisor type that can run this guest architecture."""

    type: str = attr(name="type", description="e.g. ``kvm`` or ``qemu``.")
    emulator: str | None = element(tag="emulator", default=None)
    machines: list[Machine] = element(tag="machine", default_factory=list)


class GuestArch(LibvirtXmlModel, tag="arch"):
    """``<arch>``: a guest architecture."""

    name: str = attr(name="name")
    wordsize: Literal["31", "32", "64"] = element(tag="wordsize")
    emulator: str | None = element(tag="emulator", default=None)
    loader: str | None = element(tag="loader", default=None)
    machines: list[Machine] = element(tag="machine", default_factory=list)
    domains: list[GuestDomain] = element(tag="domain", default_factory=list)


class FeatureToggle(LibvirtXmlModel):
    """Base of the guest features that can be toggled."""

    toggle: YesNo = attr(name="toggle")
    default: OnOff = attr(name="default")


class AcpiToggle(FeatureToggle, tag="acpi"):
    """``<acpi>``."""


class ApicToggle(FeatureToggle, tag="apic"):
    """``<apic>``."""


class DisksnapshotToggle(FeatureToggle, tag="disksnapshot"):
    """``<disksnapshot>``."""


class HapToggle(FeatureToggle, tag="hap"):
    """``<hap>``."""


class GuestFeatures(LibvirtXmlModel, tag="features"):
    """``<features>``: the guest features the hypervisor offers."""

    pae: PresenceFlag | None = element(tag="pae", default=None)
    nonpae: PresenceFlag | None = element(tag="nonpae", default=None)
    ia64_be: PresenceFlag | None = element(tag="ia64_be", default=None)
    acpi: AcpiToggle | None = element(tag="acpi", default=None)
    apic: ApicToggle | None = element(tag="apic", default=None)
    cpuselection: PresenceFlag | None = element(tag="cpuselection", default=None)
    deviceboot: PresenceFlag | None = element(tag="deviceboot", default=None)
    disksnapshot: DisksnapshotToggle | None = element(tag="disksnapshot", default=None)
    hap: HapToggle | None = element(tag="hap", default=None)
    external_snapshot: PresenceFlag | None = element(
        tag="externalSnapshot", default=None
    )


class GuestCapabilities(LibvirtXmlModel, tag="guest"):
    """``<guest>``: one guest OS type and architecture."""

    os_type: Literal["xen", "linux", "hvm", "exe", "uml"] = element(tag="os_type")
    arch: GuestArch = element(tag="arch")
    features: GuestFeatures | None = element(tag="features", default=None)


class Capabilities(LibvirtXmlModel, tag="capabilities"):
    """``<capabilities>``: the host and the guests it can run."""

    host: HostCapabilities = element(tag="host")
    guests: list[GuestCapabilities] = element(tag="guest", default_factory=list)
