"""What the clients send and receive.

A ``Request`` is one call to the daemon: the libvirt procedure name and its
arguments. The prototype uses plain Python values for arguments and replies;
the protocol layer will replace them with the generated XDR structs without
changing the operations (they only build ``Request`` objects).
"""

from collections.abc import Generator, Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol, TypeVar

__all__ = [
    "AsyncTransport",
    "Handle",
    "Operation",
    "Request",
    "Transport",
]

T = TypeVar("T")


@dataclass(frozen=True)
class Request:
    """One call to the daemon, as it would go on the wire."""

    procedure: str
    """The libvirt procedure, e.g. ``"domain_lookup_by_name"``."""

    arguments: Mapping[str, object] = field(default_factory=dict)
    """The arguments by name; XML travels as ``str``."""

    stream: Literal["read", "write", "both"] | None = None
    """For a call that opens a data stream: which way the data flows, as seen by
    the client. The transport answers with the open stream instead of a value."""


@dataclass(frozen=True)
class Handle:
    """A server object, as the daemon names it in follow-up requests."""

    name: str
    uuid: str | None = None
    id: int | None = None
    parent: str | None = None
    """The pool of a volume or the domain of a snapshot."""
    native: object = field(default=None, compare=False, repr=False)
    """The daemon's own description of the object, for the wire transport."""


Operation = Generator[Request, object, T]
"""A sans-I/O operation: yields ``Request``s, receives their replies, returns ``T``."""


class Transport(Protocol):
    """Sends a request and waits for the reply (used by ``LibvirtClient``)."""

    def call(self, request: Request) -> object:
        """Send ``request`` and return the daemon's reply.

        :param request: the call to make.
        :returns: the reply: a ``Handle``, a ``list`` of them, text, a number...
        :raises LibvirtError: if the daemon reports an error.
        """
        ...

    def close(self) -> None:
        """Close the connection."""
        ...


class AsyncTransport(Protocol):
    """Sends a request and awaits the reply (used by ``AsyncLibvirtClient``)."""

    async def call(self, request: Request) -> object:
        """Send ``request`` and return the daemon's reply.

        :param request: the call to make.
        :returns: the reply: a ``Handle``, a ``list`` of them, text, a number...
        :raises LibvirtError: if the daemon reports an error.
        """
        ...

    async def close(self) -> None:
        """Close the connection."""
        ...
