"""Operations on host network interfaces beyond the basic ones."""

from libvirtpy.client.operations._common import as_bool, on_host_interface
from libvirtpy.client.references import HostInterfaceRef
from libvirtpy.client.transport import Operation, Request

__all__ = [
    "begin_host_interface_changes",
    "commit_host_interface_changes",
    "is_host_interface_active",
    "rollback_host_interface_changes",
]


def is_host_interface_active(interface: HostInterfaceRef) -> Operation[bool]:
    """Tell whether a host network interface is up.

    :param interface: the interface, by name or MAC address.
    :returns: ``True`` if it is active.
    """
    return as_bool((yield from on_host_interface(interface, "interface_is_active")))


def begin_host_interface_changes(*, flags: int = 0) -> Operation[None]:
    """Start a transaction of host network changes (they can be rolled back).

    :param flags: reserved, 0.
    """
    yield Request("interface_change_begin", {"flags": flags})


def commit_host_interface_changes(*, flags: int = 0) -> Operation[None]:
    """Keep the host network changes made since ``begin_host_interface_changes``.

    :param flags: reserved, 0.
    """
    yield Request("interface_change_commit", {"flags": flags})


def rollback_host_interface_changes(*, flags: int = 0) -> Operation[None]:
    """Undo the host network changes made since ``begin_host_interface_changes``.

    :param flags: reserved, 0.
    """
    yield Request("interface_change_rollback", {"flags": flags})
