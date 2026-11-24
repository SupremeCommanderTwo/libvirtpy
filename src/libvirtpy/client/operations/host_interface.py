"""Operations on the network interfaces of the host."""

from libvirtpy.client.operations._common import (
    ACTIVE,
    INACTIVE,
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    one_handle,
)
from libvirtpy.client.references import (
    HostInterfaceRef,
    host_interface_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.interface import HostInterface

__all__ = [
    "define_host_interface",
    "destroy_host_interface",
    "list_host_interfaces",
    "lookup_host_interface",
    "start_host_interface",
    "undefine_host_interface",
]


def lookup_host_interface(interface: HostInterfaceRef) -> Operation[HostInterface]:
    """Return a network interface of the host.

    :param interface: a device name or MAC address, or a ``HostInterface`` model.
    :returns: the interface.
    :raises NoInterfaceError: if there is no such interface.
    """
    handle = yield from one_handle(host_interface_lookup(interface))
    return (yield from fetch_model("interface_get_xml_desc", handle, HostInterface))


def list_host_interfaces(
    *, active: bool | None = None
) -> Operation[list[HostInterface]]:
    """Return the network interfaces of the host.

    :param active: ``True`` for active interfaces only, ``False`` for the others,
        ``None`` for all.
    :returns: the interfaces.
    """
    flags = {True: ACTIVE, False: INACTIVE, None: 0}[active]
    handles = yield from many_handles(
        Request("connect_list_all_interfaces", {"need_results": 1, "flags": flags})
    )
    return (yield from fetch_models("interface_get_xml_desc", handles, HostInterface))


def define_host_interface(
    interface: HostInterface | str, *, flags: int = 0
) -> Operation[HostInterface]:
    """Define (or redefine) a host network interface.

    :param interface: the configuration, as a model or XML text.
    :param flags: reserved, ``0``.
    :returns: the stored configuration.
    """
    xml = as_xml(interface)
    handle = yield from one_handle(
        Request("interface_define_xml", {"xml": xml, "flags": flags})
    )
    return (yield from fetch_model("interface_get_xml_desc", handle, HostInterface))


def undefine_host_interface(interface: HostInterfaceRef) -> Operation[None]:
    """Remove the definition of a host network interface.

    :param interface: the interface.
    """
    handle = yield from one_handle(host_interface_lookup(interface))
    yield Request("interface_undefine", {"iface": handle})


def start_host_interface(interface: HostInterfaceRef) -> Operation[HostInterface]:
    """Bring a host network interface up.

    :param interface: the interface.
    :returns: the interface, now active.
    :raises OperationInvalidError: if it is already active.
    """
    handle = yield from one_handle(host_interface_lookup(interface))
    yield Request("interface_create", {"iface": handle, "flags": 0})
    return (yield from fetch_model("interface_get_xml_desc", handle, HostInterface))


def destroy_host_interface(interface: HostInterfaceRef) -> Operation[None]:
    """Bring a host network interface down.

    :param interface: the interface.
    :raises OperationInvalidError: if it is not active.
    """
    handle = yield from one_handle(host_interface_lookup(interface))
    yield Request("interface_destroy", {"iface": handle, "flags": 0})
