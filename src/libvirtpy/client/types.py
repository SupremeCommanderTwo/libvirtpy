"""Plain result types of the client that are not XML models."""

from dataclasses import dataclass
from enum import IntEnum

from libvirtpy.rpc.typed_params import TypedValue

__all__ = ["DomainInfo", "DomainState", "JobStats", "VcpuStatus"]


class DomainState(IntEnum):
    """The run state of a domain (``virDomainState``)."""

    NOSTATE = 0
    RUNNING = 1
    BLOCKED = 2
    PAUSED = 3
    SHUTDOWN = 4
    SHUTOFF = 5
    CRASHED = 6
    PMSUSPENDED = 7


@dataclass(frozen=True)
class DomainInfo:
    """Run time numbers of a domain (``virDomainInfo``)."""

    state: DomainState
    max_memory_kib: int
    memory_kib: int
    vcpus: int
    cpu_time_ns: int


@dataclass(frozen=True)
class JobStats:
    """The progress of a long-running job of a domain (``virDomainGetJobStats``)."""

    type: int
    """``virDomainJobType``: 0 none, 1 bounded, 2 unbounded, 3 completed, 4 failed,
    5 cancelled."""
    parameters: dict[str, TypedValue]
    """The statistics by name, e.g. ``time_elapsed`` or ``data_total``."""


@dataclass(frozen=True)
class VcpuStatus:
    """One virtual CPU of a running domain (``virDomainGetVcpus``)."""

    number: int
    """The vCPU number inside the domain."""
    state: int
    """``virVcpuState``: 0 offline, 1 running, 2 blocked."""
    cpu_time_ns: int
    """CPU time used, in nanoseconds."""
    running_on: int
    """The host CPU it runs on; negative if not running."""
    pinned_to: list[int]
    """The host CPUs it may run on."""
