"""Guest NUMA topology: ``<cpu><numa>``.

See https://libvirt.org/formatdomain.html#cpu-model-and-topology
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import SizeUnit, YesNo

__all__ = [
    "Numa",
    "NumaBandwidth",
    "NumaCache",
    "NumaCacheLine",
    "NumaCacheSize",
    "NumaCell",
    "NumaDistances",
    "NumaInterconnects",
    "NumaLatency",
    "NumaMemNode",
    "NumaSibling",
    "NumaTune",
    "NumaTuneMemory",
]

InterconnectType = Literal["access", "read", "write"]


class NumaSibling(LibvirtXmlModel, tag="sibling"):
    """``<sibling>``: the distance from this cell to cell ``id``."""

    id: int = attr(name="id", ge=0)
    value: int = attr(name="value", ge=10, le=255)


class NumaDistances(LibvirtXmlModel, tag="distances"):
    """``<distances>``: NUMA distances from this cell. Since 3.10.0."""

    siblings: list[NumaSibling] = element(tag="sibling", default_factory=list)


class NumaCacheSize(LibvirtXmlModel, tag="size"):
    value: int = attr(name="value", ge=0)
    unit: SizeUnit = attr(name="unit")


class NumaCacheLine(LibvirtXmlModel, tag="line"):
    value: int = attr(name="value", ge=0)
    unit: SizeUnit = attr(name="unit")


class NumaCache(LibvirtXmlModel, tag="cache"):
    """``<cache>`` in a NUMA ``<cell>``: a memory side cache. Since 6.6.0."""

    level: int = attr(name="level", ge=0)
    associativity: Literal["none", "direct", "full"] = attr(name="associativity")
    policy: Literal["none", "writeback", "writethrough"] = attr(name="policy")
    size: NumaCacheSize = element(tag="size")
    line: NumaCacheLine = element(tag="line")


class NumaCell(LibvirtXmlModel, tag="cell"):
    """``<cell>``: one guest NUMA node."""

    id: int | None = attr(name="id", default=None, ge=0)
    cpus: str | None = attr(
        name="cpus", default=None, description="vCPUs of the cell, e.g. ``0-3``."
    )
    memory: int = attr(name="memory", ge=0, description="Amount, in ``unit``.")
    unit: SizeUnit | None = attr(name="unit", default=None)
    mem_access: Literal["shared", "private"] | None = attr(
        name="memAccess", default=None
    )
    discard: YesNo | None = attr(name="discard", default=None)
    distances: NumaDistances | None = element(tag="distances", default=None)
    caches: list[NumaCache] = element(tag="cache", default_factory=list)


class NumaLatency(LibvirtXmlModel, tag="latency"):
    """``<latency>``: access latency between two cells, in nanoseconds."""

    initiator: int = attr(name="initiator", ge=0)
    target: int = attr(name="target", ge=0)
    cache: int | None = attr(name="cache", default=None, ge=0)
    type: InterconnectType = attr(name="type")
    value: int = attr(name="value", ge=0)


class NumaBandwidth(LibvirtXmlModel, tag="bandwidth"):
    """``<bandwidth>``: bandwidth between two cells, in ``unit`` per second."""

    initiator: int = attr(name="initiator", ge=0)
    target: int = attr(name="target", ge=0)
    cache: int | None = attr(name="cache", default=None, ge=0)
    type: InterconnectType = attr(name="type")
    value: int = attr(name="value", ge=0)
    unit: SizeUnit = attr(name="unit")


class NumaInterconnects(LibvirtXmlModel, tag="interconnects"):
    """``<interconnects>``: Heterogeneous Memory Attribute Table data."""

    latencies: list[NumaLatency] = element(tag="latency", default_factory=list)
    bandwidths: list[NumaBandwidth] = element(tag="bandwidth", default_factory=list)


class Numa(LibvirtXmlModel, tag="numa"):
    """``<numa>`` in ``<cpu>``: the guest NUMA topology."""

    cells: list[NumaCell] = element(tag="cell", default_factory=list)
    interconnects: NumaInterconnects | None = element(tag="interconnects", default=None)


NumaMode = Literal["strict", "preferred", "interleave", "restrictive"]


class NumaTuneMemory(LibvirtXmlModel, tag="memory"):
    """``<memory>`` of ``<numatune>``: the default NUMA policy of the guest."""

    mode: NumaMode | None = attr(name="mode", default=None)
    placement: Literal["static", "auto"] | None = attr(name="placement", default=None)
    nodeset: str | None = attr(name="nodeset", default=None)


class NumaMemNode(LibvirtXmlModel, tag="memnode"):
    """``<memnode>``: the NUMA policy of one guest node."""

    cellid: int = attr(name="cellid", ge=0)
    mode: NumaMode = attr(name="mode")
    nodeset: str = attr(name="nodeset")


class NumaTune(LibvirtXmlModel, tag="numatune"):
    """``<numatune>``: how guest memory is placed on host NUMA nodes."""

    memory: NumaTuneMemory | None = element(tag="memory", default=None)
    memnodes: list[NumaMemNode] = element(tag="memnode", default_factory=list)
