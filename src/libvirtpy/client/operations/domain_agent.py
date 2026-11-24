"""Operations that talk to the guest agent inside a domain."""

from libvirtpy.client.operations._common import as_int, as_list, as_text, on_domain
from libvirtpy.client.references import DomainRef
from libvirtpy.client.transport import Operation

__all__ = [
    "freeze_domain_filesystems",
    "get_domain_authorized_ssh_keys",
    "set_domain_agent_timeout",
    "set_domain_authorized_ssh_keys",
    "thaw_domain_filesystems",
    "trim_domain_filesystems",
]


def freeze_domain_filesystems(
    domain: DomainRef, mount_points: list[str] | None = None, *, flags: int = 0
) -> Operation[int]:
    """Freeze the file systems of the guest, so a consistent backup can be taken.

    :param domain: the domain.
    :param mount_points: the file systems; ``None`` for all.
    :param flags: reserved, 0.
    :returns: how many file systems were frozen.
    """
    reply = yield from on_domain(
        domain, "domain_fsfreeze", mountpoints=mount_points or [], flags=flags
    )
    return as_int(reply)


def thaw_domain_filesystems(
    domain: DomainRef, mount_points: list[str] | None = None, *, flags: int = 0
) -> Operation[int]:
    """Thaw file systems that ``freeze_domain_filesystems`` froze.

    :param domain: the domain.
    :param mount_points: the file systems; ``None`` for all.
    :param flags: reserved, 0.
    :returns: how many file systems were thawed.
    """
    reply = yield from on_domain(
        domain, "domain_fsthaw", mountpoints=mount_points or [], flags=flags
    )
    return as_int(reply)


def trim_domain_filesystems(
    domain: DomainRef,
    mount_point: str | None = None,
    minimum: int = 0,
    *,
    flags: int = 0,
) -> Operation[None]:
    """Tell the guest to discard unused blocks (``fstrim``).

    :param domain: the domain.
    :param mount_point: the file system; ``None`` for all.
    :param minimum: the smallest free range to discard, in bytes.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain,
        "domain_fstrim",
        mount_point=mount_point,
        minimum=minimum,
        flags=flags,
    )


def get_domain_authorized_ssh_keys(
    domain: DomainRef, user: str, *, flags: int = 0
) -> Operation[list[str]]:
    """Read the authorized SSH keys of a user in the guest.

    :param domain: the domain.
    :param user: the user name in the guest.
    :param flags: reserved, 0.
    :returns: the keys, one per entry.
    """
    reply = yield from on_domain(
        domain, "domain_authorized_ssh_keys_get", user=user, flags=flags
    )
    return [as_text(key) for key in as_list(reply)]


def set_domain_authorized_ssh_keys(
    domain: DomainRef, user: str, keys: list[str], *, flags: int = 0
) -> Operation[None]:
    """Change the authorized SSH keys of a user in the guest.

    :param domain: the domain.
    :param user: the user name in the guest.
    :param keys: the keys.
    :param flags: ``virDomainAuthorizedSSHKeysSetFlags``: 1 append, 2 remove.
    """
    yield from on_domain(
        domain, "domain_authorized_ssh_keys_set", user=user, keys=keys, flags=flags
    )


def set_domain_agent_timeout(
    domain: DomainRef, timeout: int, *, flags: int = 0
) -> Operation[None]:
    """Set how long libvirt waits for the guest agent to answer.

    :param domain: the domain.
    :param timeout: seconds; ``virDomainAgentResponseTimeoutValues``: 0 no wait,
        -1 block, -2 default.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain, "domain_agent_set_response_timeout", timeout=timeout, flags=flags
    )
