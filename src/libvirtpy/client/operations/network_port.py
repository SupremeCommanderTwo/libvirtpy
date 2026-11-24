"""Operations on the ports of a virtual network."""

from functools import partial

from libvirtpy.client.operations._common import (
    as_handle,
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    on_network_port,
    on_object,
    one_handle,
    read_parameters,
)
from libvirtpy.client.references import (
    NetworkPortRef,
    NetworkRef,
    network_lookup,
    network_port_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.rpc.typed_params import TypedValue, to_wire
from libvirtpy.xml.network import NetworkPort

__all__ = [
    "create_network_port",
    "delete_network_port",
    "get_network_port_parameters",
    "list_network_ports",
    "lookup_network_port",
    "set_network_port_parameters",
]


def list_network_ports(
    network: NetworkRef, *, flags: int = 0
) -> Operation[list[NetworkPort]]:
    """Return the ports of a network.

    :param network: the network.
    :param flags: reserved, 0.
    :returns: the ports.
    """
    handle = yield from one_handle(network_lookup(network))
    ports = yield from many_handles(
        Request(
            "network_list_all_ports",
            {"network": handle, "need_results": 1, "flags": flags},
        )
    )
    return (yield from fetch_models("network_port_get_xml_desc", ports, NetworkPort))


def lookup_network_port(
    network: NetworkRef, port: NetworkPortRef
) -> Operation[NetworkPort]:
    """Return one port of a network.

    :param network: the network.
    :param port: the port's UUID, or a ``NetworkPort`` model.
    :returns: the port.
    :raises NoNetworkPortError: if there is no such port.
    """
    network_handle = yield from one_handle(network_lookup(network))
    found = yield from one_handle(network_port_lookup(network_handle, port))
    return (yield from fetch_model("network_port_get_xml_desc", found, NetworkPort))


def create_network_port(
    network: NetworkRef, port: NetworkPort | str, *, flags: int = 0
) -> Operation[NetworkPort]:
    """Create a port on a network.

    :param network: the network.
    :param port: the port description, as a model or XML.
    :param flags: ``virNetworkPortCreateFlags``: 1 validate.
    :returns: the port as the daemon created it.
    """
    created = yield from as_handle(
        on_object(
            network_lookup(network),
            "network",
            "network_port_create_xml",
            {"xml": as_xml(port), "flags": flags},
        )
    )
    return (yield from fetch_model("network_port_get_xml_desc", created, NetworkPort))


def delete_network_port(
    network: NetworkRef, port: NetworkPortRef, *, flags: int = 0
) -> Operation[None]:
    """Delete a port of a network.

    :param network: the network.
    :param port: the port's UUID, or a ``NetworkPort`` model.
    :param flags: reserved, 0.
    """
    yield from on_network_port(network, port, "network_port_delete", flags=flags)


def get_network_port_parameters(
    network: NetworkRef, port: NetworkPortRef, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return the bandwidth limits of a port.

    :param network: the network.
    :param port: the port's UUID, or a ``NetworkPort`` model.
    :param flags: reserved, 0.
    :returns: ``inbound.average``, ``outbound.peak``, ...
    """
    return (
        yield from read_parameters(
            partial(on_network_port, network, port),
            "network_port_get_parameters",
            flags,
        )
    )


def set_network_port_parameters(
    network: NetworkRef,
    port: NetworkPortRef,
    parameters: dict[str, TypedValue],
    *,
    flags: int = 0,
) -> Operation[None]:
    """Change the bandwidth limits of a port.

    :param network: the network.
    :param port: the port's UUID, or a ``NetworkPort`` model.
    :param parameters: e.g. ``{"inbound.average": 1000}``.
    :param flags: reserved, 0.
    """
    yield from on_network_port(
        network,
        port,
        "network_port_set_parameters",
        params=to_wire(parameters),
        flags=flags,
    )
