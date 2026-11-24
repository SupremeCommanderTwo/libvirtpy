"""Operations that read or change parts of a virtual network."""

from libvirtpy.client.operations._common import (
    as_bool,
    as_list,
    as_struct,
    as_text,
    on_network,
    on_object,
)
from libvirtpy.client.references import NetworkRef, network_lookup
from libvirtpy.client.transport import Operation
from libvirtpy.rpc.protocol import types

__all__ = [
    "get_network_bridge_name",
    "get_network_metadata",
    "is_network_active",
    "is_network_persistent",
    "list_network_dhcp_leases",
    "set_network_metadata",
    "update_network",
]


def get_network_bridge_name(network: NetworkRef) -> Operation[str]:
    """Return the name of the bridge device of a network.

    :param network: the network.
    :returns: e.g. ``virbr0``.
    """
    return as_text((yield from on_network(network, "network_get_bridge_name")))


def is_network_active(network: NetworkRef) -> Operation[bool]:
    """Tell whether a network is started.

    :param network: the network.
    :returns: ``True`` if it is active.
    """
    return as_bool((yield from on_network(network, "network_is_active")))


def is_network_persistent(network: NetworkRef) -> Operation[bool]:
    """Tell whether a network has a stored configuration.

    :param network: the network.
    :returns: ``True`` if persistent, ``False`` if transient.
    """
    return as_bool((yield from on_network(network, "network_is_persistent")))


def update_network(
    network: NetworkRef,
    command: int,
    section: int,
    xml: str,
    *,
    parent_index: int = -1,
    flags: int = 0,
) -> Operation[None]:
    """Change part of a network's configuration, without redefining it.

    :param network: the network.
    :param command: ``virNetworkUpdateCommand``: 1 modify, 2 delete, 3 add last,
        4 add first.
    :param section: ``virNetworkUpdateSection``: 1 bridge, 2 domain, 3 ip,
        4 ip dhcp host, 5 ip dhcp range, 6 forward, ...
    :param xml: the XML of the element to add, modify or delete.
    :param parent_index: which parent element, or -1 for any.
    :param flags: ``virNetworkUpdateFlags``: live, config.
    """
    yield from on_network(
        network,
        "network_update",
        command=command,
        section=section,
        parent_index=parent_index,
        xml=xml,
        flags=flags,
    )


def list_network_dhcp_leases(
    network: NetworkRef, mac: str | None = None, *, flags: int = 0
) -> Operation[list[types.NetworkDhcpLease]]:
    """List the DHCP leases a network has given out.

    :param network: the network.
    :param mac: only the leases of this MAC address; ``None`` for all.
    :param flags: reserved, 0.
    :returns: each lease's ``ipaddr``, ``mac``, ``hostname``, ``expirytime``...
    """
    reply = yield from on_network(
        network, "network_get_dhcp_leases", mac=mac, need_results=1, flags=flags
    )
    return [as_struct(item, types.NetworkDhcpLease) for item in as_list(reply)]


def get_network_metadata(
    network: NetworkRef,
    metadata_type: int = 0,
    namespace: str | None = None,
    *,
    flags: int = 0,
) -> Operation[str]:
    """Read the metadata of a network.

    :param network: the network.
    :param metadata_type: ``virNetworkMetadataType``: 0 description, 1 title,
        2 an element (then give ``namespace``).
    :param namespace: the XML namespace URI of an element; ``None`` otherwise.
    :param flags: ``virNetworkUpdateFlags``: live, config.
    :returns: the text or the XML of the element.
    """
    reply = yield from on_object(
        network_lookup(network),
        "network",
        "network_get_metadata",
        {"type": metadata_type, "uri": namespace, "flags": flags},
    )
    return as_text(reply)


def set_network_metadata(
    network: NetworkRef,
    metadata_type: int,
    value: str | None,
    *,
    key: str | None = None,
    namespace: str | None = None,
    flags: int = 0,
) -> Operation[None]:
    """Set the metadata of a network.

    :param network: the network.
    :param metadata_type: ``virNetworkMetadataType``: 0 description, 1 title,
        2 an element (then give ``key`` and ``namespace``).
    :param value: the text or the XML of the element; ``None`` removes it.
    :param key: the namespace prefix of an element.
    :param namespace: the XML namespace URI of an element.
    :param flags: ``virNetworkUpdateFlags``: live, config.
    """
    yield from on_object(
        network_lookup(network),
        "network",
        "network_set_metadata",
        {
            "type": metadata_type,
            "metadata": value,
            "key": key,
            "uri": namespace,
            "flags": flags,
        },
    )
