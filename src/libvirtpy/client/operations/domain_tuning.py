"""Operations that tune the CPU, memory and scheduling of a domain."""

from collections.abc import Iterable

from libvirtpy.client.operations._common import (
    as_bytes,
    as_int,
    as_list,
    as_params,
    as_struct,
    as_text,
    get_typed_parameters,
    on_domain,
)
from libvirtpy.client.references import DomainRef
from libvirtpy.client.transport import Operation, Request
from libvirtpy.client.types import VcpuStatus
from libvirtpy.rpc.cpumap import from_cpumap, map_length, to_cpumap
from libvirtpy.rpc.protocol import types
from libvirtpy.rpc.typed_params import TypedValue, from_wire, to_wire

__all__ = [
    "add_domain_iothread",
    "delete_domain_iothread",
    "get_domain_blkio_parameters",
    "get_domain_cpu_stats",
    "get_domain_emulator_pin",
    "get_domain_guest_vcpus",
    "get_domain_memory_parameters",
    "get_domain_memory_stats",
    "get_domain_numa_parameters",
    "get_domain_scheduler_parameters",
    "get_domain_scheduler_type",
    "get_domain_vcpu_count",
    "get_domain_vcpu_pins",
    "get_domain_vcpus",
    "peek_domain_memory",
    "pin_domain_emulator",
    "pin_domain_iothread",
    "pin_domain_vcpu",
    "set_domain_blkio_parameters",
    "set_domain_guest_vcpus",
    "set_domain_iothread_parameters",
    "set_domain_max_memory",
    "set_domain_memory_parameters",
    "set_domain_numa_parameters",
    "set_domain_scheduler_parameters",
    "set_domain_vcpu",
]


def get_domain_vcpu_count(domain: DomainRef, *, flags: int = 0) -> Operation[int]:
    """Return the number of virtual CPUs of a domain.

    :param domain: the domain.
    :param flags: ``virDomainVcpuFlags``: live, config, maximum, guest.
    :returns: the count.
    """
    return as_int((yield from on_domain(domain, "domain_get_vcpus_flags", flags=flags)))


def get_domain_vcpus(domain: DomainRef) -> Operation[list[VcpuStatus]]:
    """Return the state of each virtual CPU of a running domain.

    :param domain: the domain.
    :returns: one entry per vCPU, with the host CPUs it is pinned to.
    """
    count = as_int((yield from on_domain(domain, "domain_get_vcpus_flags", flags=1)))
    length = yield from _host_map_length()
    reply = yield from on_domain(
        domain, "domain_get_vcpus", maxinfo=count, maplen=length
    )

    vcpus = as_struct(reply, types.DomainGetVcpusRet)
    maps = [vcpus.cpumaps[i * length : (i + 1) * length] for i in range(count)]
    return [
        VcpuStatus(
            item.number, item.state, item.cpu_time, item.cpu, from_cpumap(bitmap)
        )
        for item, bitmap in zip(vcpus.info, maps, strict=False)
    ]


def pin_domain_vcpu(
    domain: DomainRef, vcpu: int, cpus: Iterable[int], *, flags: int = 0
) -> Operation[None]:
    """Restrict a virtual CPU to some host CPUs.

    :param domain: the domain.
    :param vcpu: the vCPU number.
    :param cpus: the host CPU numbers it may run on.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain,
        "domain_pin_vcpu_flags",
        vcpu=vcpu,
        cpumap=to_cpumap(cpus),
        flags=flags,
    )


def get_domain_vcpu_pins(
    domain: DomainRef, *, flags: int = 0
) -> Operation[list[list[int]]]:
    """Return the host CPUs each virtual CPU may run on.

    :param domain: the domain.
    :param flags: ``virDomainModificationImpact``: live, config.
    :returns: for each vCPU, the host CPU numbers.
    """
    count = as_int((yield from on_domain(domain, "domain_get_vcpus_flags", flags=1)))
    length = yield from _host_map_length()
    reply = yield from on_domain(
        domain, "domain_get_vcpu_pin_info", ncpumaps=count, maplen=length, flags=flags
    )

    pins = as_struct(reply, types.DomainGetVcpuPinInfoRet)
    return [
        from_cpumap(pins.cpumaps[i * length : (i + 1) * length])
        for i in range(pins.num)
    ]


def pin_domain_emulator(
    domain: DomainRef, cpus: Iterable[int], *, flags: int = 0
) -> Operation[None]:
    """Restrict the emulator threads of a domain to some host CPUs.

    :param domain: the domain.
    :param cpus: the host CPU numbers.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain, "domain_pin_emulator", cpumap=to_cpumap(cpus), flags=flags
    )


def get_domain_emulator_pin(
    domain: DomainRef, *, flags: int = 0
) -> Operation[list[int]]:
    """Return the host CPUs the emulator threads of a domain may run on.

    :param domain: the domain.
    :param flags: ``virDomainModificationImpact``: live, config.
    :returns: the host CPU numbers.
    """
    length = yield from _host_map_length()
    reply = yield from on_domain(
        domain, "domain_get_emulator_pin_info", maplen=length, flags=flags
    )
    return from_cpumap(as_bytes(reply))


def get_domain_guest_vcpus(
    domain: DomainRef, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Ask the guest agent which virtual CPUs the guest has online.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: ``vcpus``, ``online``, ``offlinable`` as CPU lists such as ``0-3``.
    """
    reply = yield from on_domain(domain, "domain_get_guest_vcpus", flags=flags)
    return as_params(reply)


def set_domain_guest_vcpus(
    domain: DomainRef, cpus: str, online: bool, *, flags: int = 0
) -> Operation[None]:
    """Bring virtual CPUs of the guest online or offline, through the guest agent.

    :param domain: the domain.
    :param cpus: the vCPUs as a list such as ``0-3,6``.
    :param online: ``True`` to bring them online, ``False`` offline.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain, "domain_set_guest_vcpus", cpumap=cpus, state=int(online), flags=flags
    )


def set_domain_vcpu(
    domain: DomainRef, cpus: str, enabled: bool, *, flags: int = 0
) -> Operation[None]:
    """Enable or disable individual virtual CPUs (hotplug).

    :param domain: the domain.
    :param cpus: the vCPUs as a list such as ``0-3,6``.
    :param enabled: ``True`` to enable them, ``False`` to disable.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain, "domain_set_vcpu", cpumap=cpus, state=int(enabled), flags=flags
    )


def set_domain_max_memory(domain: DomainRef, kib: int) -> Operation[None]:
    """Set the maximum memory of a domain, in its next configuration.

    :param domain: the domain.
    :param kib: the limit in KiB.
    """
    yield from on_domain(domain, "domain_set_max_memory", memory=kib)


def get_domain_memory_stats(
    domain: DomainRef, *, max_stats: int = 16, flags: int = 0
) -> Operation[list[types.DomainMemoryStat]]:
    """Return the memory statistics the balloon driver reports.

    :param domain: the domain.
    :param max_stats: how many statistics to ask for.
    :param flags: reserved, 0.
    :returns: ``(tag, val)`` pairs; ``tag`` is ``virDomainMemoryStatTags``
        (0 swap in, 1 swap out, 4 unused, 5 available, 7 rss...), ``val`` in KiB.
    """
    reply = yield from on_domain(
        domain, "domain_memory_stats", max_stats=max_stats, flags=flags
    )
    return [as_struct(item, types.DomainMemoryStat) for item in as_list(reply)]


def peek_domain_memory(
    domain: DomainRef, offset: int, size: int, *, flags: int = 1
) -> Operation[bytes]:
    """Read memory of a domain.

    :param domain: the domain.
    :param offset: the address to start at.
    :param size: how many bytes.
    :param flags: ``virDomainMemoryFlag``: 1 virtual, 2 physical addresses.
    :returns: the bytes.
    """
    reply = yield from on_domain(
        domain, "domain_memory_peek", offset=offset, size=size, flags=flags
    )
    return as_bytes(reply)


def get_domain_memory_parameters(
    domain: DomainRef, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return the memory tuning of a domain.

    :param domain: the domain.
    :param flags: ``virDomainModificationImpact``: live, config.
    :returns: e.g. ``hard_limit``, ``soft_limit``, ``swap_hard_limit`` in KiB.
    """
    return (
        yield from get_typed_parameters(domain, "domain_get_memory_parameters", flags)
    )


def set_domain_memory_parameters(
    domain: DomainRef, parameters: dict[str, TypedValue], *, flags: int = 0
) -> Operation[None]:
    """Change the memory tuning of a domain.

    :param domain: the domain.
    :param parameters: e.g. ``{"hard_limit": 4194304}``; KiB.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain, "domain_set_memory_parameters", params=to_wire(parameters), flags=flags
    )


def get_domain_numa_parameters(
    domain: DomainRef, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return the NUMA tuning of a domain.

    :param domain: the domain.
    :param flags: ``virDomainModificationImpact``: live, config.
    :returns: ``numa_mode`` and ``numa_nodeset``.
    """
    return (
        yield from get_typed_parameters(domain, "domain_get_numa_parameters", flags)
    )


def set_domain_numa_parameters(
    domain: DomainRef, parameters: dict[str, TypedValue], *, flags: int = 0
) -> Operation[None]:
    """Change the NUMA tuning of a domain.

    :param domain: the domain.
    :param parameters: ``numa_mode`` (``virDomainNumatuneMemMode``) and
        ``numa_nodeset`` (e.g. ``"0-1"``).
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain, "domain_set_numa_parameters", params=to_wire(parameters), flags=flags
    )


def get_domain_blkio_parameters(
    domain: DomainRef, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return the block I/O tuning of a domain.

    :param domain: the domain.
    :param flags: ``virDomainModificationImpact``: live, config.
    :returns: ``weight``, ``device_weight``, ``device_read_iops_sec``...
    """
    return (
        yield from get_typed_parameters(domain, "domain_get_blkio_parameters", flags)
    )


def set_domain_blkio_parameters(
    domain: DomainRef, parameters: dict[str, TypedValue], *, flags: int = 0
) -> Operation[None]:
    """Change the block I/O tuning of a domain.

    :param domain: the domain.
    :param parameters: e.g. ``{"weight": 500}``.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain, "domain_set_blkio_parameters", params=to_wire(parameters), flags=flags
    )


def get_domain_scheduler_type(domain: DomainRef) -> Operation[str]:
    """Return the name of the CPU scheduler tuning of a domain.

    :param domain: the domain.
    :returns: e.g. ``posix`` for the Linux scheduler.
    """
    reply = yield from on_domain(domain, "domain_get_scheduler_type")
    return as_text(as_struct(reply, types.DomainGetSchedulerTypeRet).type)


def get_domain_scheduler_parameters(
    domain: DomainRef, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return the CPU scheduler tuning of a domain.

    :param domain: the domain.
    :param flags: ``virDomainModificationImpact``: live, config.
    :returns: ``cpu_shares``, ``vcpu_period``, ``vcpu_quota``, ...
    """
    reply = yield from on_domain(domain, "domain_get_scheduler_type")
    count = as_struct(reply, types.DomainGetSchedulerTypeRet).nparams
    parameters = yield from on_domain(
        domain, "domain_get_scheduler_parameters_flags", nparams=count, flags=flags
    )
    return as_params(parameters)


def set_domain_scheduler_parameters(
    domain: DomainRef, parameters: dict[str, TypedValue], *, flags: int = 0
) -> Operation[None]:
    """Change the CPU scheduler tuning of a domain.

    :param domain: the domain.
    :param parameters: e.g. ``{"cpu_shares": 2048, "vcpu_quota": 50000}``.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain,
        "domain_set_scheduler_parameters_flags",
        params=to_wire(parameters),
        flags=flags,
    )


def get_domain_cpu_stats(
    domain: DomainRef, *, start_cpu: int = -1, count: int = 1, flags: int = 0
) -> Operation[list[dict[str, TypedValue]]]:
    """Return the CPU time statistics of a domain.

    :param domain: the domain.
    :param start_cpu: the first host CPU; -1 for the totals of the whole domain.
    :param count: how many CPUs; 1 with ``start_cpu=-1``.
    :param flags: reserved, 0.
    :returns: one dict per CPU: ``cpu_time``, ``user_time``, ``system_time``...
    """
    first = yield from on_domain(
        domain,
        "domain_get_cpu_stats",
        nparams=0,
        start_cpu=0,
        ncpus=1,
        flags=flags,
    )
    per_cpu = as_struct(first, types.DomainGetCpuStatsRet).nparams

    reply = yield from on_domain(
        domain,
        "domain_get_cpu_stats",
        nparams=per_cpu,
        start_cpu=start_cpu,
        ncpus=count,
        flags=flags,
    )
    values = from_wire(as_struct(reply, types.DomainGetCpuStatsRet).params)
    return _split_per_cpu(values, per_cpu, count)


def pin_domain_iothread(
    domain: DomainRef, iothread_id: int, cpus: Iterable[int], *, flags: int = 0
) -> Operation[None]:
    """Restrict an IO thread of a domain to some host CPUs.

    :param domain: the domain.
    :param iothread_id: the IO thread id.
    :param cpus: the host CPU numbers.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain,
        "domain_pin_iothread",
        iothreads_id=iothread_id,
        cpumap=to_cpumap(cpus),
        flags=flags,
    )


def add_domain_iothread(
    domain: DomainRef, iothread_id: int, *, flags: int = 0
) -> Operation[None]:
    """Add an IO thread to a domain.

    :param domain: the domain.
    :param iothread_id: the id of the new IO thread.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain, "domain_add_iothread", iothread_id=iothread_id, flags=flags
    )


def delete_domain_iothread(
    domain: DomainRef, iothread_id: int, *, flags: int = 0
) -> Operation[None]:
    """Remove an IO thread from a domain.

    :param domain: the domain.
    :param iothread_id: the IO thread id.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain, "domain_del_iothread", iothread_id=iothread_id, flags=flags
    )


def set_domain_iothread_parameters(
    domain: DomainRef,
    iothread_id: int,
    parameters: dict[str, TypedValue],
    *,
    flags: int = 0,
) -> Operation[None]:
    """Tune an IO thread of a domain.

    :param domain: the domain.
    :param iothread_id: the IO thread id.
    :param parameters: e.g. ``{"poll_max_ns": 32768}``.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain,
        "domain_set_iothread_params",
        iothread_id=iothread_id,
        params=to_wire(parameters),
        flags=flags,
    )


def _host_map_length() -> Operation[int]:
    """Find how many bytes a CPU bitmap of the host needs.

    :returns: the length, from the host's CPU count.
    """
    reply = yield Request("node_get_info")
    node = as_struct(reply, types.NodeGetInfoRet)
    return map_length(node.nodes * node.sockets * node.cores * node.threads)


def _split_per_cpu(
    values: dict[str, TypedValue], per_cpu: int, count: int
) -> list[dict[str, TypedValue]]:
    """Split the flat statistics into one dict per CPU.

    :param values: the statistics of all asked CPUs, in order.
    :param per_cpu: how many parameters each CPU has.
    :param count: how many CPUs were asked.
    :returns: one dict per CPU.
    """
    items = list(values.items())
    return [dict(items[i * per_cpu : (i + 1) * per_cpu]) for i in range(count)]
