"""Operations on virtual networks."""

from libvirtpy.client.operations._common import (
    ACTIVE,
    INACTIVE,
    as_int,
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    one_handle,
)
from libvirtpy.client.references import (
    NetworkRef,
    network_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.network import Network

__all__ = [
    "create_network",
    "define_network",
    "destroy_network",
    "get_network_autostart",
    "list_networks",
    "lookup_network",
    "set_network_autostart",
    "start_network",
    "undefine_network",
]


def lookup_network(network: NetworkRef) -> Operation[Network]:
    """Return the configuration of a virtual network.

    :param network: a name, UUID or ``Network`` model.
    :returns: the network.
    :raises NoNetworkError: if there is no such network.
    """
    handle = yield from one_handle(network_lookup(network))
    return (yield from fetch_model("network_get_xml_desc", handle, Network))


def list_networks(*, active: bool | None = None) -> Operation[list[Network]]:
    """Return the virtual networks.

    :param active: ``True`` for active networks only, ``False`` for the others,
        ``None`` for all.
    :returns: the networks.
    """
    flags = {True: ACTIVE, False: INACTIVE, None: 0}[active]
    handles = yield from many_handles(
        Request("connect_list_all_networks", {"need_results": 1, "flags": flags})
    )
    return (yield from fetch_models("network_get_xml_desc", handles, Network))


def define_network(network: Network | str, *, flags: int = 0) -> Operation[Network]:
    """Define (or redefine) a persistent network without starting it.

    :param network: the configuration, as a model or XML text.
    :param flags: ``virNetworkDefineFlags``.
    :returns: the stored configuration, with what libvirt filled in.
    """
    xml = as_xml(network)
    handle = yield from one_handle(
        Request("network_define_xml_flags", {"xml": xml, "flags": flags})
    )
    return (yield from fetch_model("network_get_xml_desc", handle, Network))


def create_network(network: Network | str, *, flags: int = 0) -> Operation[Network]:
    """Start a transient network: it disappears when it stops.

    :param network: the configuration, as a model or XML text.
    :param flags: ``virNetworkCreateFlags``.
    :returns: the running network.
    """
    xml = as_xml(network)
    handle = yield from one_handle(
        Request("network_create_xml_flags", {"xml": xml, "flags": flags})
    )
    return (yield from fetch_model("network_get_xml_desc", handle, Network))


def undefine_network(network: NetworkRef) -> Operation[None]:
    """Remove a persistent network's definition.

    :param network: the network.
    :raises OperationInvalidError: if the network is active.
    """
    handle = yield from one_handle(network_lookup(network))
    yield Request("network_undefine", {"net": handle})


def start_network(network: NetworkRef) -> Operation[Network]:
    """Start a defined network.

    :param network: the network.
    :returns: the network, now active.
    :raises OperationInvalidError: if the network is already active.
    """
    handle = yield from one_handle(network_lookup(network))
    yield Request("network_create", {"net": handle})
    return (yield from fetch_model("network_get_xml_desc", handle, Network))


def destroy_network(network: NetworkRef) -> Operation[None]:
    """Stop a network.

    :param network: the network.
    :raises OperationInvalidError: if the network is not active.
    """
    handle = yield from one_handle(network_lookup(network))
    yield Request("network_destroy", {"net": handle})


def get_network_autostart(network: NetworkRef) -> Operation[bool]:
    """Tell whether a network starts with the host.

    :param network: the network.
    :returns: ``True`` if it starts at boot.
    """
    handle = yield from one_handle(network_lookup(network))
    return bool(as_int((yield Request("network_get_autostart", {"net": handle}))))


def set_network_autostart(network: NetworkRef, enabled: bool) -> Operation[None]:
    """Make a network start (or not) with the host.

    :param network: the network.
    :param enabled: ``True`` to start it at boot.
    """
    handle = yield from one_handle(network_lookup(network))
    yield Request("network_set_autostart", {"net": handle, "autostart": int(enabled)})
