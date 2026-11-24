"""Operations on the disks of a running domain: statistics, resizing, block jobs."""

from libvirtpy.client.operations._common import (
    as_bytes,
    as_list,
    as_struct,
    get_typed_parameters,
    on_domain,
)
from libvirtpy.client.references import DomainRef
from libvirtpy.client.transport import Operation
from libvirtpy.rpc.protocol import types
from libvirtpy.rpc.typed_params import TypedValue, to_wire

__all__ = [
    "abort_domain_block_job",
    "commit_domain_block",
    "copy_domain_block",
    "delete_domain_throttle_group",
    "detach_domain_device_by_alias",
    "get_domain_block_info",
    "get_domain_block_io_tune",
    "get_domain_block_job_info",
    "get_domain_block_stats",
    "get_domain_disk_errors",
    "peek_domain_block",
    "pull_domain_block",
    "rebase_domain_block",
    "resize_domain_block",
    "set_domain_block_io_tune",
    "set_domain_block_job_speed",
    "set_domain_block_threshold",
    "set_domain_throttle_group",
]


def get_domain_block_stats(
    domain: DomainRef, disk: str, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return the I/O statistics of a disk of a running domain.

    :param domain: the domain.
    :param disk: the disk, by target name (``vda``) or image path.
    :param flags: reserved, 0.
    :returns: ``rd_bytes``, ``rd_operations``, ``wr_bytes``, ``wr_operations``...
    """
    return (
        yield from get_typed_parameters(
            domain, "domain_block_stats_flags", flags, path=disk
        )
    )


def get_domain_block_info(
    domain: DomainRef, disk: str, *, flags: int = 0
) -> Operation[types.DomainGetBlockInfoRet]:
    """Return the size of a disk.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param flags: reserved, 0.
    :returns: ``capacity`` (virtual size), ``allocation`` (used by the guest) and
        ``physical`` (on the host), all in bytes.
    """
    reply = yield from on_domain(
        domain, "domain_get_block_info", path=disk, flags=flags
    )
    return as_struct(reply, types.DomainGetBlockInfoRet)


def resize_domain_block(
    domain: DomainRef, disk: str, size: int, *, flags: int = 0
) -> Operation[None]:
    """Change the virtual size of a disk of a running domain.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param size: the new size, in KiB unless ``flags`` has the bytes bit.
    :param flags: ``virDomainBlockResizeFlags``: 1 the size is in bytes.
    """
    yield from on_domain(
        domain, "domain_block_resize", disk=disk, size=size, flags=flags
    )


def peek_domain_block(
    domain: DomainRef, disk: str, offset: int, size: int, *, flags: int = 0
) -> Operation[bytes]:
    """Read bytes from a disk of a domain.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param offset: where to start, in bytes.
    :param size: how many bytes.
    :param flags: reserved, 0.
    :returns: the bytes.
    """
    reply = yield from on_domain(
        domain, "domain_block_peek", path=disk, offset=offset, size=size, flags=flags
    )
    return as_bytes(reply)


def get_domain_block_io_tune(
    domain: DomainRef, disk: str | None = None, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return the I/O limits of a disk.

    :param domain: the domain.
    :param disk: the disk, by target name; ``None`` for the number of disks only.
    :param flags: ``virDomainModificationImpact``: live, config.
    :returns: ``total_bytes_sec``, ``read_iops_sec``, ``group_name``...
    """
    return (
        yield from get_typed_parameters(
            domain, "domain_get_block_io_tune", flags, disk=disk
        )
    )


def set_domain_block_io_tune(
    domain: DomainRef,
    disk: str,
    parameters: dict[str, TypedValue],
    *,
    flags: int = 0,
) -> Operation[None]:
    """Change the I/O limits of a disk.

    :param domain: the domain.
    :param disk: the disk, by target name.
    :param parameters: e.g. ``{"total_bytes_sec": 10_000_000}``.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain,
        "domain_set_block_io_tune",
        disk=disk,
        params=to_wire(parameters),
        flags=flags,
    )


def abort_domain_block_job(
    domain: DomainRef, disk: str, *, flags: int = 0
) -> Operation[None]:
    """Cancel the active block job (pull, copy, commit) of a disk.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param flags: ``virDomainBlockJobAbortFlags``: async, pivot.
    """
    yield from on_domain(domain, "domain_block_job_abort", path=disk, flags=flags)


def get_domain_block_job_info(
    domain: DomainRef, disk: str, *, flags: int = 0
) -> Operation[types.DomainGetBlockJobInfoRet]:
    """Return the progress of the block job of a disk.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param flags: ``virDomainBlockJobInfoFlags``: 1 the bandwidth in bytes.
    :returns: ``found`` (0 if no job), ``type``, ``bandwidth``, and ``cur`` out of
        ``end`` for the progress.
    """
    reply = yield from on_domain(
        domain, "domain_get_block_job_info", path=disk, flags=flags
    )
    return as_struct(reply, types.DomainGetBlockJobInfoRet)


def set_domain_block_job_speed(
    domain: DomainRef, disk: str, bandwidth: int, *, flags: int = 0
) -> Operation[None]:
    """Limit the speed of the block job of a disk.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param bandwidth: MiB per second (bytes with the flag); 0 for no limit.
    :param flags: ``virDomainBlockJobSetSpeedFlags``: 1 the bandwidth in bytes.
    """
    yield from on_domain(
        domain,
        "domain_block_job_set_speed",
        path=disk,
        bandwidth=bandwidth,
        flags=flags,
    )


def pull_domain_block(
    domain: DomainRef, disk: str, bandwidth: int = 0, *, flags: int = 0
) -> Operation[None]:
    """Copy the backing chain into a disk image, so it stands alone.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param bandwidth: MiB per second; 0 for no limit.
    :param flags: ``virDomainBlockPullFlags``.
    """
    yield from on_domain(
        domain, "domain_block_pull", path=disk, bandwidth=bandwidth, flags=flags
    )


def rebase_domain_block(
    domain: DomainRef,
    disk: str,
    base: str | None = None,
    bandwidth: int = 0,
    *,
    flags: int = 0,
) -> Operation[None]:
    """Change the backing file of a disk, copying data as needed.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param base: the new backing image; ``None`` flattens the chain.
    :param bandwidth: MiB per second; 0 for no limit.
    :param flags: ``virDomainBlockRebaseFlags``: shallow, relative, copy...
    """
    yield from on_domain(
        domain,
        "domain_block_rebase",
        path=disk,
        base=base,
        bandwidth=bandwidth,
        flags=flags,
    )


def commit_domain_block(
    domain: DomainRef,
    disk: str,
    base: str | None = None,
    top: str | None = None,
    bandwidth: int = 0,
    *,
    flags: int = 0,
) -> Operation[None]:
    """Merge a layer of a disk's backing chain into a lower one.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param base: the image to merge into; ``None`` for the bottom of the chain.
    :param top: the image to merge from; ``None`` for the active layer.
    :param bandwidth: MiB per second; 0 for no limit.
    :param flags: ``virDomainBlockCommitFlags``: shallow, delete, active, relative.
    """
    yield from on_domain(
        domain,
        "domain_block_commit",
        disk=disk,
        base=base,
        top=top,
        bandwidth=bandwidth,
        flags=flags,
    )


def copy_domain_block(
    domain: DomainRef,
    disk: str,
    destination: str,
    parameters: dict[str, TypedValue] | None = None,
    *,
    flags: int = 0,
) -> Operation[None]:
    """Copy a disk to a new destination while the domain runs.

    :param domain: the domain.
    :param disk: the disk, by target name or image path.
    :param destination: the destination disk as XML (``<disk>`` element).
    :param parameters: ``bandwidth``, ``granularity``, ``buf-size``.
    :param flags: ``virDomainBlockCopyFlags``: shallow, reuse external, ...
    """
    yield from on_domain(
        domain,
        "domain_block_copy",
        path=disk,
        destxml=destination,
        params=to_wire(parameters or {}),
        flags=flags,
    )


def set_domain_block_threshold(
    domain: DomainRef, device: str, threshold: int, *, flags: int = 0
) -> Operation[None]:
    """Ask for an event when a disk's usage passes a threshold.

    :param domain: the domain.
    :param device: the disk target (``vda``) or an image ``vda[1]``.
    :param threshold: the limit in bytes; 0 clears it.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain,
        "domain_set_block_threshold",
        dev=device,
        threshold=threshold,
        flags=flags,
    )


def get_domain_disk_errors(
    domain: DomainRef, *, max_errors: int = 64, flags: int = 0
) -> Operation[list[types.DomainDiskError]]:
    """List the disks of a domain that report errors.

    :param domain: the domain.
    :param max_errors: how many to ask for at most.
    :param flags: reserved, 0.
    :returns: ``(disk, error)`` pairs; ``error`` is ``virDomainDiskErrorCode``.
    """
    reply = yield from on_domain(
        domain, "domain_get_disk_errors", maxerrors=max_errors, flags=flags
    )
    result = as_struct(reply, types.DomainGetDiskErrorsRet)
    return [as_struct(item, types.DomainDiskError) for item in as_list(result.errors)]


def set_domain_throttle_group(
    domain: DomainRef,
    group: str,
    parameters: dict[str, TypedValue],
    *,
    flags: int = 0,
) -> Operation[None]:
    """Create or change a group of disks that share I/O limits.

    :param domain: the domain.
    :param group: the group name.
    :param parameters: the limits, e.g. ``{"total_bytes_sec": 1_000_000}``.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain,
        "domain_set_throttle_group",
        group=group,
        params=to_wire(parameters),
        flags=flags,
    )


def delete_domain_throttle_group(
    domain: DomainRef, group: str | None = None, *, flags: int = 0
) -> Operation[None]:
    """Remove a group of disks that share I/O limits.

    :param domain: the domain.
    :param group: the group name.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(domain, "domain_del_throttle_group", group=group, flags=flags)


def detach_domain_device_by_alias(
    domain: DomainRef, alias: str, *, flags: int = 0
) -> Operation[None]:
    """Unplug a device by its alias (``ua-...``) instead of its XML.

    :param domain: the domain.
    :param alias: the device alias.
    :param flags: ``virDomainDeviceModifyFlags``: live, config.
    """
    yield from on_domain(domain, "domain_detach_device_alias", alias=alias, flags=flags)
