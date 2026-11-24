"""The description of one remote procedure: its number, types and daemon."""

from dataclasses import dataclass
from typing import Any, Literal, TypeVar

__all__ = ["Driver", "Procedure"]

Driver = Literal[
    "hypervisor", "interface", "network", "node_device", "nwfilter", "secret", "storage"
]
"""The daemon that serves a procedure when libvirt runs as modular daemons."""

ArgsT = TypeVar("ArgsT")
ReturnT = TypeVar("ReturnT")


@dataclass(frozen=True)
class Procedure[ArgsT, ReturnT]:
    """A call of the remote protocol. ``args`` and ``ret`` are ``None`` if void."""

    number: int
    name: str
    args: type[ArgsT] | None
    ret: type[ReturnT] | None
    driver: Driver
    message: type[Any] | None = None
    """For an event: the struct the daemon pushes (it is not a reply)."""
