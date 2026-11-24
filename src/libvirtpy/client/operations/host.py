"""Operations on the host itself: CPUs, memory, huge pages, suspend."""

from libvirtpy.client.operations._common import (
    as_int,
    as_list,
    as_struct,
    parameter_count,
    parameters_of,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.rpc.protocol import types
from libvirtpy.rpc.typed_params import TypedValue, from_wire, to_wire

__all__ = [
    "allocate_host_pages",
    "get_host_cells_free_memory",
    "get_host_cpu_map",
    "get_host_cpu_stats",
    "get_host_free_memory",
    "get_host_free_pages",
    "get_host_info",
    "get_host_memory_parameters",
    "get_host_memory_stats",
    "get_host_security_model",
    "get_host_sev_info",
    "set_host_memory_parameters",
    "suspend_host_for_duration",
]


def get_host_info() -> Operation[types.NodeGetInfoRet]:
    """Return the hardware summary of the host.

    :returns: ``model`` (CPU model as character codes), ``memory`` (KiB), ``cpus``,
        ``mhz``, ``nodes``, ``sockets``, ``cores`` and ``threads``.
    """
    return as_struct((yield Request("node_get_info")), types.NodeGetInfoRet)


def get_host_free_memory() -> Operation[int]:
    """Return the free memory of the host.

    :returns: the free memory in bytes.
    """
    reply = yield Request("node_get_free_memory")
    return as_int(reply)


def get_host_cells_free_memory(
    start_cell: int = 0, max_cells: int = 64
) -> Operation[list[int]]:
    """Return the free memory of each NUMA cell of the host.

    :param start_cell: the first cell.
    :param max_cells: how many cells to ask for at most.
    :returns: the free memory of each cell, in bytes.
    """
    reply = yield Request(
        "node_get_cells_free_memory", {"start_cell": start_cell, "maxcells": max_cells}
    )
    return [as_int(item) for item in as_list(reply)]


def get_host_cpu_stats(cpu: int = -1, *, flags: int = 0) -> Operation[dict[str, int]]:
    """Return the CPU time statistics of the host.

    :param cpu: the host CPU number; -1 for all together.
    :param flags: reserved, 0.
    :returns: ``kernel``, ``user``, ``idle``, ``iowait``, ``intr`` in nanoseconds.
    """
    first = yield Request(
        "node_get_cpu_stats", {"cpu_num": cpu, "nparams": 0, "flags": flags}
    )
    reply = yield Request(
        "node_get_cpu_stats",
        {"cpu_num": cpu, "nparams": parameter_count(first), "flags": flags},
    )
    return _name_value_pairs(reply)


def get_host_memory_stats(
    cell: int = -1, *, flags: int = 0
) -> Operation[dict[str, int]]:
    """Return the memory statistics of the host.

    :param cell: the NUMA cell; -1 for the whole host.
    :param flags: reserved, 0.
    :returns: ``total``, ``free``, ``buffers``, ``cached`` in KiB.
    """
    first = yield Request(
        "node_get_memory_stats", {"nparams": 0, "cell_num": cell, "flags": flags}
    )
    reply = yield Request(
        "node_get_memory_stats",
        {"nparams": parameter_count(first), "cell_num": cell, "flags": flags},
    )
    return _name_value_pairs(reply)


def get_host_memory_parameters(*, flags: int = 0) -> Operation[dict[str, TypedValue]]:
    """Return the memory sharing (KSM) settings of the host.

    :param flags: reserved, 0.
    :returns: ``shm_pages_to_scan``, ``shm_sleep_millisecs``, ...
    """
    first = yield Request("node_get_memory_parameters", {"nparams": 0, "flags": flags})
    reply = yield Request(
        "node_get_memory_parameters",
        {"nparams": parameter_count(first), "flags": flags},
    )
    return from_wire(parameters_of(reply))


def set_host_memory_parameters(
    parameters: dict[str, TypedValue], *, flags: int = 0
) -> Operation[None]:
    """Change the memory sharing (KSM) settings of the host.

    :param parameters: e.g. ``{"shm_sleep_millisecs": 20}``.
    :param flags: reserved, 0.
    """
    yield Request(
        "node_set_memory_parameters", {"params": to_wire(parameters), "flags": flags}
    )


def get_host_cpu_map(*, flags: int = 0) -> Operation[types.NodeGetCpuMapRet]:
    """Return which host CPUs exist and which are online.

    :param flags: reserved, 0.
    :returns: ``cpumap`` (a bit mask of online CPUs), ``online`` (their count) and
        the total in ``ret``.
    """
    reply = yield Request(
        "node_get_cpu_map", {"need_map": 1, "need_online": 1, "flags": flags}
    )
    return as_struct(reply, types.NodeGetCpuMapRet)


def get_host_security_model() -> Operation[types.NodeGetSecurityModelRet]:
    """Return the security driver of the host.

    :returns: ``model`` and ``doi`` as character codes.
    """
    reply = yield Request("node_get_security_model")
    return as_struct(reply, types.NodeGetSecurityModelRet)


def get_host_free_pages(
    page_sizes: list[int], start_cell: int = 0, cell_count: int = 1, *, flags: int = 0
) -> Operation[list[int]]:
    """Return how many pages of each size are free.

    :param page_sizes: the page sizes in KiB (4, 2048, 1048576...).
    :param start_cell: the first NUMA cell.
    :param cell_count: how many cells.
    :param flags: reserved, 0.
    :returns: the free page counts, for each cell and size.
    """
    reply = yield Request(
        "node_get_free_pages",
        {
            "pages": page_sizes,
            "start_cell": start_cell,
            "cell_count": cell_count,
            "flags": flags,
        },
    )
    return [as_int(item) for item in as_list(reply)]


def allocate_host_pages(
    page_sizes: list[int],
    page_counts: list[int],
    start_cell: int = 0,
    cell_count: int = 1,
    *,
    flags: int = 0,
) -> Operation[int]:
    """Reserve huge pages on the host.

    :param page_sizes: the page sizes in KiB.
    :param page_counts: how many pages of each size.
    :param start_cell: the first NUMA cell.
    :param cell_count: how many cells.
    :param flags: ``virNodeAllocPagesFlags``: 1 add, 2 set.
    :returns: how many pages were allocated.
    """
    reply = yield Request(
        "node_alloc_pages",
        {
            "page_sizes": page_sizes,
            "page_counts": page_counts,
            "start_cell": start_cell,
            "cell_count": cell_count,
            "flags": flags,
        },
    )
    return as_int(reply)


def get_host_sev_info(*, flags: int = 0) -> Operation[dict[str, TypedValue]]:
    """Return the AMD SEV capabilities of the host.

    :param flags: reserved, 0.
    :returns: ``cert-chain``, ``cbitpos``, ``reduced-phys-bits``...
    """
    first = yield Request("node_get_sev_info", {"nparams": 0, "flags": flags})
    reply = yield Request(
        "node_get_sev_info", {"nparams": parameter_count(first), "flags": flags}
    )
    return from_wire(parameters_of(reply))


def suspend_host_for_duration(
    target: int, duration: int, *, flags: int = 0
) -> Operation[None]:
    """Suspend the whole host for a time.

    :param target: ``virNodeSuspendTarget``: 0 memory, 1 disk, 2 hybrid.
    :param duration: seconds until it wakes up.
    :param flags: reserved, 0.
    """
    yield Request(
        "node_suspend_for_duration",
        {"target": target, "duration": duration, "flags": flags},
    )


def _name_value_pairs(reply: object) -> dict[str, int]:
    """Make a dict from the ``(field, value)`` list of a host statistics reply.

    :param reply: a return struct with a ``params`` list of ``field``/``value``.
    :returns: the statistics by name.
    :raises TypeError: if the reply is not of that shape.
    """
    items = getattr(reply, "params", None)
    if not isinstance(items, list):
        raise TypeError(f"expected a reply with params, got {reply!r}")

    statistics = {}
    for item in items:
        if not isinstance(item, types.NodeGetCpuStats | types.NodeGetMemoryStats):
            raise TypeError(f"expected a statistic, got {item!r}")
        statistics[item.field] = item.value
    return statistics
