"""Operations that read facts about a domain."""

from libvirtpy.client.operations._common import (
    as_bool,
    as_int,
    as_list,
    as_params,
    as_struct,
    as_text,
    on_domain,
)
from libvirtpy.client.references import DomainRef
from libvirtpy.client.transport import Operation
from libvirtpy.client.types import JobStats
from libvirtpy.rpc.protocol import types
from libvirtpy.rpc.typed_params import TypedValue, from_wire, to_wire

__all__ = [
    "abort_domain_job",
    "get_domain_control_info",
    "get_domain_fsinfo",
    "get_domain_guest_info",
    "get_domain_hostname",
    "get_domain_iothread_info",
    "get_domain_job_info",
    "get_domain_job_stats",
    "get_domain_launch_security_info",
    "get_domain_max_memory",
    "get_domain_max_vcpus",
    "get_domain_messages",
    "get_domain_metadata",
    "get_domain_os_type",
    "get_domain_perf_events",
    "get_domain_security_label",
    "get_domain_security_labels",
    "get_domain_time",
    "has_domain_current_snapshot",
    "is_domain_active",
    "is_domain_persistent",
    "is_domain_updated",
    "set_domain_memory_stats_period",
    "set_domain_metadata",
    "set_domain_perf_events",
    "set_domain_time",
    "start_domain_dirty_rate_calc",
]


def is_domain_active(domain: DomainRef) -> Operation[bool]:
    """Tell whether the domain is running (or paused).

    :param domain: the domain.
    :returns: ``True`` if it is active.
    """
    return as_bool((yield from on_domain(domain, "domain_is_active")))


def is_domain_persistent(domain: DomainRef) -> Operation[bool]:
    """Tell whether the domain has a stored configuration (it survives a stop).

    :param domain: the domain.
    :returns: ``True`` if it is persistent, ``False`` if transient.
    """
    return as_bool((yield from on_domain(domain, "domain_is_persistent")))


def is_domain_updated(domain: DomainRef) -> Operation[bool]:
    """Tell whether the stored configuration differs from the running one.

    :param domain: the domain.
    :returns: ``True`` if a restart would change something.
    """
    return as_bool((yield from on_domain(domain, "domain_is_updated")))


def get_domain_max_memory(domain: DomainRef) -> Operation[int]:
    """Return the maximum memory of a domain.

    :param domain: the domain.
    :returns: the limit in KiB.
    """
    return as_int((yield from on_domain(domain, "domain_get_max_memory")))


def get_domain_max_vcpus(domain: DomainRef) -> Operation[int]:
    """Return the maximum number of virtual CPUs the domain can have.

    :param domain: the domain.
    :returns: the limit.
    """
    return as_int((yield from on_domain(domain, "domain_get_max_vcpus")))


def get_domain_os_type(domain: DomainRef) -> Operation[str]:
    """Return the operating system type of a domain.

    :param domain: the domain.
    :returns: e.g. ``hvm`` or ``linux``.
    """
    return as_text((yield from on_domain(domain, "domain_get_os_type")))


def get_domain_control_info(
    domain: DomainRef, *, flags: int = 0
) -> Operation[types.DomainGetControlInfoRet]:
    """Return the state of the control interface to the hypervisor.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: ``state`` (``virDomainControlState``), ``details`` and ``state_time``
        (milliseconds since the state began).
    """
    reply = yield from on_domain(domain, "domain_get_control_info", flags=flags)
    return as_struct(reply, types.DomainGetControlInfoRet)


def get_domain_hostname(domain: DomainRef, *, flags: int = 0) -> Operation[str]:
    """Ask the guest for its host name.

    :param domain: the domain.
    :param flags: ``virDomainGetHostnameFlags``: guest agent or lease.
    :returns: the host name.
    """
    return as_text((yield from on_domain(domain, "domain_get_hostname", flags=flags)))


def get_domain_job_info(domain: DomainRef) -> Operation[types.DomainGetJobInfoRet]:
    """Return the progress of the current job (migration, save, dump...).

    :param domain: the domain.
    :returns: the job ``type`` and its time and data counters, as the daemon sends
        them.
    """
    reply = yield from on_domain(domain, "domain_get_job_info")
    return as_struct(reply, types.DomainGetJobInfoRet)


def get_domain_job_stats(domain: DomainRef, *, flags: int = 0) -> Operation[JobStats]:
    """Return detailed statistics of the current or the last completed job.

    :param domain: the domain.
    :param flags: ``virDomainGetJobStatsFlags``: 1 the last completed job.
    :returns: the job type and its statistics by name.
    """
    reply = yield from on_domain(domain, "domain_get_job_stats", flags=flags)
    stats = as_struct(reply, types.DomainGetJobStatsRet)
    return JobStats(type=stats.type, parameters=from_wire(stats.params))


def abort_domain_job(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Cancel the current job of a domain.

    :param domain: the domain.
    :param flags: ``virDomainAbortJobFlagsValues``: 1 postcopy.
    """
    yield from on_domain(domain, "domain_abort_job_flags", flags=flags)


def get_domain_time(
    domain: DomainRef, *, flags: int = 0
) -> Operation[types.DomainGetTimeRet]:
    """Read the clock of the guest, through the guest agent.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: ``seconds`` and ``nseconds`` since the epoch.
    """
    reply = yield from on_domain(domain, "domain_get_time", flags=flags)
    return as_struct(reply, types.DomainGetTimeRet)


def set_domain_time(
    domain: DomainRef, seconds: int, nanoseconds: int = 0, *, flags: int = 0
) -> Operation[None]:
    """Set the clock of the guest, through the guest agent.

    :param domain: the domain.
    :param seconds: seconds since the epoch.
    :param nanoseconds: the fraction, in nanoseconds.
    :param flags: ``virDomainSetTimeFlags``: 1 sync from the host clock.
    """
    yield from on_domain(
        domain, "domain_set_time", seconds=seconds, nseconds=nanoseconds, flags=flags
    )


def get_domain_iothread_info(
    domain: DomainRef, *, flags: int = 0
) -> Operation[list[types.DomainIothreadInfo]]:
    """List the IO threads of a domain and the host CPUs each may use.

    :param domain: the domain.
    :param flags: ``virDomainModificationImpact``: live or config.
    :returns: one entry per IO thread: ``iothread_id`` and ``cpumap`` (a bit mask).
    """
    reply = yield from on_domain(domain, "domain_get_iothread_info", flags=flags)
    return [as_struct(item, types.DomainIothreadInfo) for item in as_list(reply)]


def get_domain_fsinfo(
    domain: DomainRef, *, flags: int = 0
) -> Operation[list[types.DomainFsinfo]]:
    """List the file systems of the guest, through the guest agent.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: mount point, name, file system type and disks of each file system.
    """
    reply = yield from on_domain(domain, "domain_get_fsinfo", flags=flags)
    return [as_struct(item, types.DomainFsinfo) for item in as_list(reply)]


def get_domain_guest_info(
    domain: DomainRef, info_types: int = 0, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Ask the guest agent for information about the guest.

    :param domain: the domain.
    :param info_types: ``virDomainGuestInfoTypes`` bits (users, os, timezone,
        hostname, file systems, disks, interfaces); 0 for all.
    :param flags: reserved, 0.
    :returns: the information by name, e.g. ``os.name``.
    """
    reply = yield from on_domain(
        domain, "domain_get_guest_info", types=info_types, flags=flags
    )
    return as_params(reply)


def get_domain_messages(domain: DomainRef, *, flags: int = 0) -> Operation[list[str]]:
    """Read the messages libvirt has for a domain (for example a failed hot-unplug).

    :param domain: the domain.
    :param flags: ``virDomainMessageType``: daemon or guest messages; 0 for all.
    :returns: the messages.
    """
    reply = yield from on_domain(domain, "domain_get_messages", flags=flags)
    return [as_text(item) for item in as_list(reply)]


def get_domain_launch_security_info(
    domain: DomainRef, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return the confidential-computing launch parameters (SEV, TDX...).

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: the parameters by name.
    """
    reply = yield from on_domain(domain, "domain_get_launch_security_info", flags=flags)
    return as_params(reply)


def get_domain_perf_events(
    domain: DomainRef, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return which performance monitoring events are enabled.

    :param domain: the domain.
    :param flags: ``virDomainModificationImpact``: live or config.
    :returns: event name (``cmt``, ``mbmt``, ``cpu_cycles``...) -> enabled.
    """
    reply = yield from on_domain(domain, "domain_get_perf_events", flags=flags)
    return as_params(reply)


def set_domain_perf_events(
    domain: DomainRef, events: dict[str, bool], *, flags: int = 0
) -> Operation[None]:
    """Enable or disable performance monitoring events.

    :param domain: the domain.
    :param events: event name -> enabled.
    :param flags: ``virDomainModificationImpact``: live or config.
    """
    yield from on_domain(
        domain, "domain_set_perf_events", params=to_wire(events), flags=flags
    )


def get_domain_security_label(
    domain: DomainRef,
) -> Operation[types.DomainGetSecurityLabelRet]:
    """Return the security label (SELinux, AppArmor) of the domain's process.

    :param domain: the domain.
    :returns: ``label`` (the text as character codes) and ``enforcing``.
    """
    reply = yield from on_domain(domain, "domain_get_security_label")
    return as_struct(reply, types.DomainGetSecurityLabelRet)


def get_domain_security_labels(
    domain: DomainRef,
) -> Operation[list[types.DomainGetSecurityLabelRet]]:
    """Return the security labels of the domain's process, one per security driver.

    :param domain: the domain.
    :returns: the labels.
    """
    reply = yield from on_domain(domain, "domain_get_security_label_list")
    return [as_struct(item, types.DomainGetSecurityLabelRet) for item in as_list(reply)]


def get_domain_metadata(
    domain: DomainRef,
    metadata_type: int = 0,
    namespace: str | None = None,
    *,
    flags: int = 0,
) -> Operation[str]:
    """Read the metadata of a domain.

    :param domain: the domain.
    :param metadata_type: ``virDomainMetadataType``: 0 description, 1 title,
        2 an element (then give ``namespace``).
    :param namespace: the XML namespace URI of an element; ``None`` otherwise.
    :param flags: ``virDomainModificationImpact``: live or config.
    :returns: the text or the XML of the element.
    """
    reply = yield from on_domain(
        domain,
        "domain_get_metadata",
        type=metadata_type,
        uri=namespace,
        flags=flags,
    )
    return as_text(reply)


def set_domain_metadata(
    domain: DomainRef,
    metadata_type: int,
    value: str | None,
    *,
    key: str | None = None,
    namespace: str | None = None,
    flags: int = 0,
) -> Operation[None]:
    """Set the metadata of a domain.

    :param domain: the domain.
    :param metadata_type: ``virDomainMetadataType``: 0 description, 1 title,
        2 an element (then give ``key`` and ``namespace``).
    :param value: the text or the XML of the element; ``None`` removes it.
    :param key: the namespace prefix of an element.
    :param namespace: the XML namespace URI of an element.
    :param flags: ``virDomainModificationImpact``: live or config.
    """
    yield from on_domain(
        domain,
        "domain_set_metadata",
        type=metadata_type,
        metadata=value,
        key=key,
        uri=namespace,
        flags=flags,
    )


def has_domain_current_snapshot(
    domain: DomainRef, *, flags: int = 0
) -> Operation[bool]:
    """Tell whether the domain has a current snapshot.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: ``True`` if there is one.
    """
    return as_bool(
        (yield from on_domain(domain, "domain_has_current_snapshot", flags=flags))
    )


def set_domain_memory_stats_period(
    domain: DomainRef, period: int, *, flags: int = 0
) -> Operation[None]:
    """Set how often the balloon driver reports memory statistics.

    :param domain: the domain.
    :param period: seconds between reports; 0 stops them, negative leaves as is.
    :param flags: ``virDomainModificationImpact``: live or config.
    """
    yield from on_domain(
        domain, "domain_set_memory_stats_period", period=period, flags=flags
    )


def start_domain_dirty_rate_calc(
    domain: DomainRef, seconds: int, *, flags: int = 0
) -> Operation[None]:
    """Start measuring how fast the guest dirties its memory.

    :param domain: the domain.
    :param seconds: how long to measure.
    :param flags: ``virDomainDirtyRateCalcFlags``: the measuring mode.
    """
    yield from on_domain(
        domain, "domain_start_dirty_rate_calc", seconds=seconds, flags=flags
    )
