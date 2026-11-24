"""Events: what the daemon tells you without being asked.

An event says that something happened to a domain, a network, a storage pool, a
host device or a secret: a domain started, a disk reported an error, a block job
finished. ``Event.data`` holds the generated message struct with every detail;
the common parts (what it is about, which kind) are plain attributes.
"""

import dataclasses
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from libvirtpy.rpc.session import ServerEvent

__all__ = [
    "SOURCES",
    "DomainEventKind",
    "DomainLifecycle",
    "Event",
    "EventSource",
    "NetworkEventKind",
    "NodeDeviceEventKind",
    "PoolEventKind",
    "SecretEventKind",
    "make_event",
]


class DomainEventKind(IntEnum):
    """The kinds of domain event (``virDomainEventID``)."""

    LIFECYCLE = 0
    REBOOT = 1
    RTC_CHANGE = 2
    WATCHDOG = 3
    IO_ERROR = 4
    GRAPHICS = 5
    IO_ERROR_REASON = 6
    CONTROL_ERROR = 7
    BLOCK_JOB = 8
    DISK_CHANGE = 9
    TRAY_CHANGE = 10
    PMWAKEUP = 11
    PMSUSPEND = 12
    BALLOON_CHANGE = 13
    PMSUSPEND_DISK = 14
    DEVICE_REMOVED = 15
    BLOCK_JOB_2 = 16
    TUNABLE = 17
    AGENT_LIFECYCLE = 18
    DEVICE_ADDED = 19
    MIGRATION_ITERATION = 20
    JOB_COMPLETED = 21
    DEVICE_REMOVAL_FAILED = 22
    METADATA_CHANGE = 23
    BLOCK_THRESHOLD = 24
    MEMORY_FAILURE = 25
    MEMORY_DEVICE_SIZE_CHANGE = 26
    NIC_MAC_CHANGE = 27
    VCPU_REMOVED = 28
    CHANNEL_LIFECYCLE = 29


class NetworkEventKind(IntEnum):
    """The kinds of network event (``virNetworkEventID``)."""

    LIFECYCLE = 0
    METADATA_CHANGE = 1


class PoolEventKind(IntEnum):
    """The kinds of storage pool event (``virStoragePoolEventID``)."""

    LIFECYCLE = 0
    REFRESH = 1


class NodeDeviceEventKind(IntEnum):
    """The kinds of host device event (``virNodeDeviceEventID``)."""

    LIFECYCLE = 0
    UPDATE = 1


class SecretEventKind(IntEnum):
    """The kinds of secret event (``virSecretEventID``)."""

    LIFECYCLE = 0
    VALUE_CHANGED = 1


class DomainLifecycle(IntEnum):
    """What happened to a domain in a ``lifecycle`` event (``virDomainEventType``)."""

    DEFINED = 0
    UNDEFINED = 1
    STARTED = 2
    SUSPENDED = 3
    RESUMED = 4
    STOPPED = 5
    SHUTDOWN = 6
    PMSUSPENDED = 7
    CRASHED = 8


@dataclass(frozen=True)
class EventSource:
    """How to subscribe to one family of events."""

    register: str
    """The procedure that starts the subscription."""
    deregister: str
    """The procedure that ends it."""
    kinds: type[IntEnum]
    """The event ids of the family."""
    object_argument: str
    """The argument of ``register`` that limits it to one object."""
    prefixes: tuple[str, ...]
    """What the procedure names of its events begin with (longest first)."""


SOURCES = {
    "domain": EventSource(
        "connect_domain_event_callback_register_any",
        "connect_domain_event_callback_deregister_any",
        DomainEventKind,
        "dom",
        ("domain_event_callback_", "domain_event_"),
    ),
    "network": EventSource(
        "connect_network_event_register_any",
        "connect_network_event_deregister_any",
        NetworkEventKind,
        "net",
        ("network_event_callback_", "network_event_"),
    ),
    "pool": EventSource(
        "connect_storage_pool_event_register_any",
        "connect_storage_pool_event_deregister_any",
        PoolEventKind,
        "pool",
        ("storage_pool_event_",),
    ),
    "node_device": EventSource(
        "connect_node_device_event_register_any",
        "connect_node_device_event_deregister_any",
        NodeDeviceEventKind,
        "dev",
        ("node_device_event_",),
    ),
    "secret": EventSource(
        "connect_secret_event_register_any",
        "connect_secret_event_deregister_any",
        SecretEventKind,
        "secret",
        ("secret_event_",),
    ),
}


@dataclass(frozen=True)
class Event:
    """Something that happened, as the daemon reported it."""

    source: str
    """``domain``, ``network``, ``pool``, ``node_device`` or ``secret``."""
    kind: str
    """The event kind in lower case: ``lifecycle``, ``block_job_2``, ``refresh``..."""
    name: str | None
    """The name of the object it is about (a secret has none; see ``uuid``)."""
    uuid: str | None
    """The UUID of the object, if it has one."""
    callback_id: int | None
    """The subscription it answers."""
    data: Any
    """The generated message struct, with all the details of the event."""

    @property
    def lifecycle(self) -> tuple[DomainLifecycle, int] | None:
        """The ``(what happened, detail)`` of a domain ``lifecycle`` event.

        :returns: e.g. ``(DomainLifecycle.STOPPED, 4)``, or ``None`` for any other
            event. ``detail`` is the libvirt reason code (for example 4 = destroyed).
        """
        message = getattr(self.data, "msg", None)
        if self.source != "domain" or self.kind != "lifecycle" or message is None:
            return None
        return DomainLifecycle(message.event), int(message.detail)


def make_event(server_event: ServerEvent) -> Event | None:
    """Turn a pushed message into an ``Event``.

    :param server_event: the decoded message of the session.
    :returns: the event, or ``None`` if the message is not one this module knows.
    """
    name = server_event.procedure.name
    for source, description in SOURCES.items():
        for prefix in description.prefixes:
            if name.startswith(prefix):
                return _build(source, name.removeprefix(prefix), server_event.message)
    return None


def callback_id_of(message: Any) -> int | None:
    """Read the subscription id out of an event message.

    :param message: a decoded event message.
    :returns: the id, or ``None`` for the old events that have none.
    """
    value = getattr(message, "callback_id", None)
    return value if isinstance(value, int) else None


def _build(source: str, kind: str, message: Any) -> Event:
    """Assemble an event from its parts.

    :param source: the event family.
    :param kind: the event kind.
    :param message: the decoded message.
    :returns: the event.
    """
    about = _find_object(message)
    uuid_bytes = getattr(about, "uuid", None)
    return Event(
        source=source,
        kind=kind,
        name=getattr(about, "name", None),
        uuid=_format_uuid(uuid_bytes) if isinstance(uuid_bytes, bytes) else None,
        callback_id=callback_id_of(message),
        data=message,
    )


def _find_object(message: Any) -> Any:
    """Find the object an event is about inside its message.

    :param message: a decoded event message.
    :returns: the ``Nonnull*`` struct of the domain, network, ...; or ``None``.
    """
    for field in dataclasses.fields(message):
        value = getattr(message, field.name)
        if type(value).__name__.startswith("Nonnull"):
            return value
        if field.name == "msg":
            return _find_object(value)
    return None


def _format_uuid(raw: bytes) -> str:
    """Write a UUID in its usual form.

    :param raw: the 16 bytes.
    :returns: e.g. ``01234567-89ab-cdef-0123-456789abcdef``.
    """
    import uuid

    return str(uuid.UUID(bytes=raw))
