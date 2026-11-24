"""Operations on the checkpoints and backups of a domain."""

from libvirtpy.client.operations._common import (
    as_handle,
    as_text,
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    on_checkpoint,
    on_domain,
    one_handle,
)
from libvirtpy.client.references import (
    CheckpointRef,
    DomainRef,
    checkpoint_lookup,
    domain_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.backup import Backup, Checkpoint

__all__ = [
    "abort_domain_backup",
    "begin_domain_backup",
    "create_domain_checkpoint",
    "delete_domain_checkpoint",
    "get_domain_backup",
    "get_domain_checkpoint_parent",
    "list_domain_checkpoint_children",
    "list_domain_checkpoints",
    "lookup_domain_checkpoint",
]


def list_domain_checkpoints(
    domain: DomainRef, *, flags: int = 0
) -> Operation[list[Checkpoint]]:
    """Return the checkpoints of a domain (dirty-block tracking points).

    :param domain: the domain.
    :param flags: ``virDomainCheckpointListFlags``: roots, leaves, topological...
    :returns: the checkpoints.
    """
    handle = yield from one_handle(domain_lookup(domain))
    handles = yield from many_handles(
        Request(
            "domain_list_all_checkpoints",
            {"dom": handle, "need_results": 1, "flags": flags},
        )
    )
    return (
        yield from fetch_models("domain_checkpoint_get_xml_desc", handles, Checkpoint)
    )


def lookup_domain_checkpoint(
    domain: DomainRef, checkpoint: CheckpointRef
) -> Operation[Checkpoint]:
    """Return one checkpoint of a domain.

    :param domain: the domain.
    :param checkpoint: the checkpoint name, or a ``Checkpoint`` model.
    :returns: the checkpoint.
    :raises NoCheckpointError: if there is no such checkpoint.
    """
    domain_handle = yield from one_handle(domain_lookup(domain))
    found = yield from one_handle(checkpoint_lookup(domain_handle, checkpoint))
    return (yield from fetch_model("domain_checkpoint_get_xml_desc", found, Checkpoint))


def create_domain_checkpoint(
    domain: DomainRef, checkpoint: Checkpoint | str, *, flags: int = 0
) -> Operation[Checkpoint]:
    """Create a checkpoint of a domain.

    :param domain: the domain.
    :param checkpoint: the checkpoint description, as a model or XML.
    :param flags: ``virDomainCheckpointCreateFlags``: redefine, quiesce...
    :returns: the checkpoint as the daemon stored it.
    """
    created = yield from as_handle(
        on_domain(
            domain,
            "domain_checkpoint_create_xml",
            xml_desc=as_xml(checkpoint),
            flags=flags,
        )
    )
    return (
        yield from fetch_model("domain_checkpoint_get_xml_desc", created, Checkpoint)
    )


def get_domain_checkpoint_parent(
    domain: DomainRef, checkpoint: CheckpointRef, *, flags: int = 0
) -> Operation[Checkpoint]:
    """Return the parent of a checkpoint.

    :param domain: the domain.
    :param checkpoint: the checkpoint.
    :param flags: reserved, 0.
    :returns: the parent checkpoint.
    :raises NoCheckpointError: if it has no parent.
    """
    parent = yield from as_handle(
        on_checkpoint(domain, checkpoint, "domain_checkpoint_get_parent", flags=flags)
    )
    return (
        yield from fetch_model("domain_checkpoint_get_xml_desc", parent, Checkpoint)
    )


def list_domain_checkpoint_children(
    domain: DomainRef, checkpoint: CheckpointRef, *, flags: int = 0
) -> Operation[list[Checkpoint]]:
    """Return the checkpoints that descend from a checkpoint.

    :param domain: the domain.
    :param checkpoint: the checkpoint.
    :param flags: ``virDomainCheckpointListFlags``: 1 all descendants, ...
    :returns: the children.
    """
    domain_handle = yield from one_handle(domain_lookup(domain))
    parent = yield from one_handle(checkpoint_lookup(domain_handle, checkpoint))
    children = yield from many_handles(
        Request(
            "domain_checkpoint_list_all_children",
            {"checkpoint": parent, "need_results": 1, "flags": flags},
        )
    )
    return (
        yield from fetch_models("domain_checkpoint_get_xml_desc", children, Checkpoint)
    )


def delete_domain_checkpoint(
    domain: DomainRef, checkpoint: CheckpointRef, *, flags: int = 0
) -> Operation[None]:
    """Delete a checkpoint.

    :param domain: the domain.
    :param checkpoint: the checkpoint.
    :param flags: ``virDomainCheckpointDeleteFlags``: children, metadata only...
    """
    yield from on_checkpoint(
        domain, checkpoint, "domain_checkpoint_delete", flags=flags
    )


def begin_domain_backup(
    domain: DomainRef,
    backup: Backup | str,
    checkpoint: Checkpoint | str | None = None,
    *,
    flags: int = 0,
) -> Operation[None]:
    """Start a backup job of a running domain.

    The job runs until it is aborted with ``abort_domain_backup``.

    :param domain: the domain.
    :param backup: the backup description (push or pull mode), as a model or XML.
    :param checkpoint: a checkpoint to create with the backup, or ``None``.
    :param flags: ``virDomainBackupBeginFlags``: reuse external.
    """
    checkpoint_xml = None if checkpoint is None else as_xml(checkpoint)
    yield from on_domain(
        domain,
        "domain_backup_begin",
        backup_xml=as_xml(backup),
        checkpoint_xml=checkpoint_xml,
        flags=flags,
    )


def get_domain_backup(domain: DomainRef, *, flags: int = 0) -> Operation[Backup]:
    """Return the description of the running backup job of a domain.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: the backup as the daemon runs it.
    """
    xml = as_text(
        (yield from on_domain(domain, "domain_backup_get_xml_desc", flags=flags))
    )
    return Backup.from_xml(xml)


def abort_domain_backup(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Cancel the running backup job of a domain.

    :param domain: the domain.
    :param flags: ``virDomainAbortJobFlagsValues``.
    """
    yield from on_domain(domain, "domain_abort_job_flags", flags=flags)
