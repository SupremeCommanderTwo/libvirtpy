"""Operations on the snapshot tree of a domain: current, parent, children."""

from libvirtpy.client.operations._common import (
    as_bool,
    as_handle,
    fetch_model,
    fetch_models,
    many_handles,
    on_domain,
    on_snapshot,
    one_handle,
)
from libvirtpy.client.references import (
    DomainRef,
    SnapshotRef,
    domain_lookup,
    snapshot_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.snapshot import Snapshot

__all__ = [
    "get_current_domain_snapshot",
    "get_domain_snapshot_parent",
    "has_domain_snapshot_metadata",
    "is_domain_snapshot_current",
    "list_domain_snapshot_children",
]


def get_current_domain_snapshot(
    domain: DomainRef, *, flags: int = 0
) -> Operation[Snapshot]:
    """Return the current snapshot of a domain.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: the snapshot.
    :raises NoSnapshotError: if the domain has no current snapshot.
    """
    handle = yield from as_handle(
        on_domain(domain, "domain_snapshot_current", flags=flags)
    )
    return (yield from fetch_model("domain_snapshot_get_xml_desc", handle, Snapshot))


def get_domain_snapshot_parent(
    domain: DomainRef, snapshot: SnapshotRef, *, flags: int = 0
) -> Operation[Snapshot]:
    """Return the parent of a snapshot.

    :param domain: the domain.
    :param snapshot: the snapshot.
    :param flags: reserved, 0.
    :returns: the parent snapshot.
    :raises NoSnapshotError: if the snapshot has no parent.
    """
    parent = yield from as_handle(
        on_snapshot(domain, snapshot, "domain_snapshot_get_parent", flags=flags)
    )
    return (yield from fetch_model("domain_snapshot_get_xml_desc", parent, Snapshot))


def list_domain_snapshot_children(
    domain: DomainRef, snapshot: SnapshotRef, *, flags: int = 0
) -> Operation[list[Snapshot]]:
    """Return the snapshots that descend from a snapshot.

    :param domain: the domain.
    :param snapshot: the snapshot.
    :param flags: ``virDomainSnapshotListFlags``: 1 all descendants, ...
    :returns: the children.
    """
    domain_handle = yield from one_handle(domain_lookup(domain))
    parent = yield from one_handle(snapshot_lookup(domain_handle, snapshot))
    children = yield from many_handles(
        Request(
            "domain_snapshot_list_all_children",
            {"snapshot": parent, "need_results": 1, "flags": flags},
        )
    )
    return (yield from fetch_models("domain_snapshot_get_xml_desc", children, Snapshot))


def is_domain_snapshot_current(
    domain: DomainRef, snapshot: SnapshotRef, *, flags: int = 0
) -> Operation[bool]:
    """Tell whether a snapshot is the current one.

    :param domain: the domain.
    :param snapshot: the snapshot.
    :param flags: reserved, 0.
    :returns: ``True`` if it is current.
    """
    reply = yield from on_snapshot(
        domain, snapshot, "domain_snapshot_is_current", flags=flags
    )
    return as_bool(reply)


def has_domain_snapshot_metadata(
    domain: DomainRef, snapshot: SnapshotRef, *, flags: int = 0
) -> Operation[bool]:
    """Tell whether libvirt keeps the metadata of a snapshot.

    :param domain: the domain.
    :param snapshot: the snapshot.
    :param flags: reserved, 0.
    :returns: ``True`` if it does.
    """
    reply = yield from on_snapshot(
        domain, snapshot, "domain_snapshot_has_metadata", flags=flags
    )
    return as_bool(reply)
