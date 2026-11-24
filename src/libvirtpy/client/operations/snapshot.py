"""Operations on the snapshots of a domain."""

from libvirtpy.client.operations._common import (
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
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
    "create_domain_snapshot",
    "delete_domain_snapshot",
    "list_domain_snapshots",
    "lookup_domain_snapshot",
    "revert_domain_snapshot",
]


def list_domain_snapshots(domain: DomainRef) -> Operation[list[Snapshot]]:
    """Return the snapshots of a domain.

    :param domain: the domain.
    :returns: the snapshots, oldest first.
    """
    handle = yield from one_handle(domain_lookup(domain))
    names = yield from many_handles(
        Request(
            "domain_list_all_snapshots", {"dom": handle, "need_results": 1, "flags": 0}
        )
    )
    return (yield from fetch_models("domain_snapshot_get_xml_desc", names, Snapshot))


def lookup_domain_snapshot(
    domain: DomainRef, snapshot: SnapshotRef
) -> Operation[Snapshot]:
    """Return one snapshot of a domain.

    :param domain: the domain.
    :param snapshot: the snapshot name, or a ``Snapshot`` model.
    :returns: the snapshot.
    :raises NoSnapshotError: if there is no such snapshot.
    """
    handle = yield from one_handle(domain_lookup(domain))
    found = yield from one_handle(snapshot_lookup(handle, snapshot))
    return (yield from fetch_model("domain_snapshot_get_xml_desc", found, Snapshot))


def create_domain_snapshot(
    domain: DomainRef, snapshot: Snapshot | str, *, flags: int = 0
) -> Operation[Snapshot]:
    """Take a snapshot of a domain.

    :param domain: the domain.
    :param snapshot: the snapshot description, as a model or XML (a name may be
        left out).
    :param flags: ``virDomainSnapshotCreateFlags``.
    :returns: the snapshot as the daemon stored it.
    """
    handle = yield from one_handle(domain_lookup(domain))
    arguments = {"dom": handle, "xml_desc": as_xml(snapshot), "flags": flags}
    created = yield from one_handle(Request("domain_snapshot_create_xml", arguments))
    return (yield from fetch_model("domain_snapshot_get_xml_desc", created, Snapshot))


def revert_domain_snapshot(
    domain: DomainRef, snapshot: SnapshotRef, *, flags: int = 0
) -> Operation[None]:
    """Return a domain to a snapshot.

    :param domain: the domain.
    :param snapshot: the snapshot name, or a ``Snapshot`` model.
    :param flags: ``virDomainSnapshotRevertFlags``.
    """
    handle = yield from one_handle(domain_lookup(domain))
    found = yield from one_handle(snapshot_lookup(handle, snapshot))
    yield Request("domain_revert_to_snapshot", {"snap": found, "flags": flags})


def delete_domain_snapshot(
    domain: DomainRef, snapshot: SnapshotRef, *, flags: int = 0
) -> Operation[None]:
    """Delete a snapshot of a domain.

    :param domain: the domain.
    :param snapshot: the snapshot name, or a ``Snapshot`` model.
    :param flags: ``virDomainSnapshotDeleteFlags``.
    """
    handle = yield from one_handle(domain_lookup(domain))
    found = yield from one_handle(snapshot_lookup(handle, snapshot))
    yield Request("domain_snapshot_delete", {"snap": found, "flags": flags})
