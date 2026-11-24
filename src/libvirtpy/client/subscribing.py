"""Planning an event subscription: which procedures, which arguments."""

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from libvirtpy.client.references import (
    domain_lookup,
    network_lookup,
    node_device_lookup,
    pool_lookup,
    secret_lookup,
)
from libvirtpy.client.transport import Handle, Request
from libvirtpy.rpc.events import SOURCES
from libvirtpy.rpc.procedure import Procedure
from libvirtpy.rpc.protocol.procedures import PROCEDURES

__all__ = ["SubscriptionPlan", "event_lookup", "plan_subscription"]

PROCEDURES_BY_NAME = {procedure.name: procedure for procedure in PROCEDURES.values()}
LOOKUPS: dict[str, Callable[[Any], Request]] = {
    "domain": domain_lookup,
    "network": network_lookup,
    "pool": pool_lookup,
    "node_device": node_device_lookup,
    "secret": secret_lookup,
}


@dataclass(frozen=True)
class SubscriptionPlan:
    """What to send to the daemon to start a subscription."""

    register: Procedure[Any, Any]
    deregister: Procedure[Any, Any]
    kinds: list[IntEnum]
    object_argument: str

    def arguments(self, handle: object) -> Iterator[dict[str, object]]:
        """Make the arguments of each registration.

        :param handle: the ``Handle`` of the object to limit the events to, or
            ``None`` for all.
        :returns: one argument dict per event kind.
        :raises TypeError: if ``handle`` is neither a handle nor ``None``.
        """
        if handle is not None and not isinstance(handle, Handle):
            raise TypeError(f"expected a Handle, got {handle!r}")

        for kind in self.kinds:
            yield {"event_id": int(kind), self.object_argument: handle}


def plan_subscription(source: str, kinds: Iterable[IntEnum] | None) -> SubscriptionPlan:
    """Work out the registrations for a source and some event kinds.

    :param source: ``domain``, ``network``, ``pool``, ``node_device`` or ``secret``.
    :param kinds: members of the source's kind enum; ``None`` for ``LIFECYCLE``.
    :returns: the plan.
    :raises ValueError: if the source or a kind is unknown.
    """
    if source not in SOURCES:
        raise ValueError(f"unknown event source {source!r}; use one of {list(SOURCES)}")

    description = SOURCES[source]
    chosen = list(kinds) if kinds is not None else [description.kinds(0)]
    for kind in chosen:
        if not isinstance(kind, description.kinds):
            raise ValueError(f"{kind!r} is not an event kind of {source!r}")

    return SubscriptionPlan(
        register=PROCEDURES_BY_NAME[description.register],
        deregister=PROCEDURES_BY_NAME[description.deregister],
        kinds=chosen,
        object_argument=description.object_argument,
    )


def event_lookup(source: str, target: object) -> Request:
    """Make the request that finds the object an event subscription is limited to.

    :param source: the event source.
    :param target: a reference of that kind of object (a name, UUID or model).
    :returns: the lookup request.
    """
    return LOOKUPS[source](target)
