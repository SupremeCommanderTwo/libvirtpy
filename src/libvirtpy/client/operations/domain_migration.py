"""Operations that tune a migration of a domain.

Starting a migration is not here: libvirt coordinates it in the client between
two daemons (the ``migrate_*3`` steps), which this library does not do yet.
"""

from libvirtpy.client.operations._common import as_int, on_domain
from libvirtpy.client.references import DomainRef
from libvirtpy.client.transport import Operation, Request
from libvirtpy.rpc.typed_params import TypedValue, to_wire

__all__ = [
    "get_domain_migration_compression_cache",
    "get_domain_migration_max_downtime",
    "get_domain_migration_max_speed",
    "restore_domain_with_parameters",
    "save_domain_with_parameters",
    "set_domain_launch_security_state",
    "set_domain_migration_compression_cache",
    "set_domain_migration_max_downtime",
    "set_domain_migration_max_speed",
    "start_domain_migration_post_copy",
]


def get_domain_migration_max_speed(
    domain: DomainRef, *, flags: int = 0
) -> Operation[int]:
    """Return the bandwidth limit of the migration of a domain.

    :param domain: the domain.
    :param flags: ``virDomainMigrateMaxSpeedFlags``: 1 post-copy.
    :returns: the limit in MiB per second; 0 for none.
    """
    reply = yield from on_domain(domain, "domain_migrate_get_max_speed", flags=flags)
    return as_int(reply)


def set_domain_migration_max_speed(
    domain: DomainRef, bandwidth: int, *, flags: int = 0
) -> Operation[None]:
    """Limit the bandwidth of the migration of a domain.

    :param domain: the domain.
    :param bandwidth: MiB per second; 0 for no limit.
    :param flags: ``virDomainMigrateMaxSpeedFlags``: 1 post-copy.
    """
    yield from on_domain(
        domain, "domain_migrate_set_max_speed", bandwidth=bandwidth, flags=flags
    )


def get_domain_migration_max_downtime(
    domain: DomainRef, *, flags: int = 0
) -> Operation[int]:
    """Return the longest pause allowed at the end of a live migration.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: the limit in milliseconds.
    """
    reply = yield from on_domain(domain, "domain_migrate_get_max_downtime", flags=flags)
    return as_int(reply)


def set_domain_migration_max_downtime(
    domain: DomainRef, downtime: int, *, flags: int = 0
) -> Operation[None]:
    """Set the longest pause allowed at the end of a live migration.

    :param domain: the domain.
    :param downtime: the limit in milliseconds.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain, "domain_migrate_set_max_downtime", downtime=downtime, flags=flags
    )


def get_domain_migration_compression_cache(
    domain: DomainRef, *, flags: int = 0
) -> Operation[int]:
    """Return the size of the cache used to compress a migration.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: the size in bytes.
    """
    reply = yield from on_domain(
        domain, "domain_migrate_get_compression_cache", flags=flags
    )
    return as_int(reply)


def set_domain_migration_compression_cache(
    domain: DomainRef, size: int, *, flags: int = 0
) -> Operation[None]:
    """Set the size of the cache used to compress a migration.

    :param domain: the domain.
    :param size: the size in bytes.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain, "domain_migrate_set_compression_cache", cache_size=size, flags=flags
    )


def start_domain_migration_post_copy(
    domain: DomainRef, *, flags: int = 0
) -> Operation[None]:
    """Switch a running live migration to post-copy mode.

    :param domain: the domain.
    :param flags: reserved, 0.
    """
    yield from on_domain(domain, "domain_migrate_start_post_copy", flags=flags)


def save_domain_with_parameters(
    domain: DomainRef, parameters: dict[str, TypedValue], *, flags: int = 0
) -> Operation[None]:
    """Save a domain to a file, with the options of the parameter form.

    :param domain: the domain.
    :param parameters: ``file`` (required), ``dom_xml``, ``bandwidth``,
        ``parallel.connections``, ...
    :param flags: ``virDomainSaveRestoreFlags``.
    """
    yield from on_domain(
        domain, "domain_save_params", params=to_wire(parameters), flags=flags
    )


def restore_domain_with_parameters(
    parameters: dict[str, TypedValue], *, flags: int = 0
) -> Operation[None]:
    """Start a domain from a save file, with the options of the parameter form.

    :param parameters: ``file`` (required), ``dom_xml``, ``bandwidth``,
        ``parallel.connections``, ...
    :param flags: ``virDomainSaveRestoreFlags``.
    """
    yield Request(
        "domain_restore_params", {"params": to_wire(parameters), "flags": flags}
    )


def set_domain_launch_security_state(
    domain: DomainRef, parameters: dict[str, TypedValue], *, flags: int = 0
) -> Operation[None]:
    """Set the launch security state of a confidential guest (e.g. its secret).

    :param domain: the domain.
    :param parameters: ``sev-secret``, ``sev-secret-header``, ``sev-secret-set-
        address``.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain,
        "domain_set_launch_security_state",
        params=to_wire(parameters),
        flags=flags,
    )
