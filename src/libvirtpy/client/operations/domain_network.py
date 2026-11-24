"""Operations on the network interfaces of a running domain."""

from libvirtpy.client.operations._common import (
    as_list,
    as_struct,
    get_typed_parameters,
    on_domain,
)
from libvirtpy.client.references import DomainRef
from libvirtpy.client.transport import Operation
from libvirtpy.rpc.protocol import types
from libvirtpy.rpc.typed_params import TypedValue, to_wire

__all__ = [
    "announce_domain_interface",
    "get_domain_interface_parameters",
    "get_domain_interface_stats",
    "list_domain_interface_addresses",
    "set_domain_interface_parameters",
]


def get_domain_interface_stats(
    domain: DomainRef, device: str
) -> Operation[types.DomainInterfaceStatsRet]:
    """Return the traffic counters of an interface of a running domain.

    :param domain: the domain.
    :param device: the host side device name (``vnet0``) or the MAC address.
    :returns: the received and transmitted bytes, packets, errors and drops.
    """
    reply = yield from on_domain(domain, "domain_interface_stats", device=device)
    return as_struct(reply, types.DomainInterfaceStatsRet)


def list_domain_interface_addresses(
    domain: DomainRef, source: int = 0, *, flags: int = 0
) -> Operation[list[types.DomainInterface]]:
    """List the IP addresses of the interfaces of a running domain.

    :param domain: the domain.
    :param source: ``virDomainInterfaceAddressesSource``: 0 DHCP lease, 1 guest
        agent, 2 ARP table.
    :param flags: reserved, 0.
    :returns: for each interface its ``name``, ``hwaddr`` and ``addrs``.
    """
    reply = yield from on_domain(
        domain, "domain_interface_addresses", source=source, flags=flags
    )
    return [as_struct(item, types.DomainInterface) for item in as_list(reply)]


def get_domain_interface_parameters(
    domain: DomainRef, device: str, *, flags: int = 0
) -> Operation[dict[str, TypedValue]]:
    """Return the bandwidth limits of an interface.

    :param domain: the domain.
    :param device: the host side device name or the MAC address.
    :param flags: ``virDomainModificationImpact``: live, config.
    :returns: ``inbound.average``, ``outbound.peak``, ...
    """
    return (
        yield from get_typed_parameters(
            domain, "domain_get_interface_parameters", flags, device=device
        )
    )


def set_domain_interface_parameters(
    domain: DomainRef,
    device: str,
    parameters: dict[str, TypedValue],
    *,
    flags: int = 0,
) -> Operation[None]:
    """Change the bandwidth limits of an interface.

    :param domain: the domain.
    :param device: the host side device name or the MAC address.
    :param parameters: e.g. ``{"inbound.average": 1000}``.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain,
        "domain_set_interface_parameters",
        device=device,
        params=to_wire(parameters),
        flags=flags,
    )


def announce_domain_interface(
    domain: DomainRef,
    device: str | None = None,
    parameters: dict[str, TypedValue] | None = None,
    *,
    flags: int = 0,
) -> Operation[None]:
    """Make the guest's interface announce itself on the network (gratuitous ARP).

    :param domain: the domain.
    :param device: the interface, by MAC address; ``None`` for all.
    :param parameters: ``rounds``, ``initial``, ``max``, ``step``.
    :param flags: ``virDomainModificationImpact``: live.
    """
    yield from on_domain(
        domain,
        "domain_announce_interface",
        device=device,
        params=to_wire(parameters or {}),
        flags=flags,
    )
