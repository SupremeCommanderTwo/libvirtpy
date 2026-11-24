"""The hand-written part of the two clients: connection handling and ``_run``.

The generated classes ``LibvirtClient`` and ``AsyncLibvirtClient`` add one
one-line method per operation of ``libvirtpy.client.operations``.
"""

from collections.abc import Iterable
from enum import IntEnum
from types import TracebackType
from typing import Protocol, TypeVar, runtime_checkable

from libvirtpy.client._runner import run_async, run_sync
from libvirtpy.client.transport import AsyncTransport, Operation, Transport
from libvirtpy.client.wire import WireTransport
from libvirtpy.client.wire_aio import AsyncWireTransport
from libvirtpy.rpc.errors import ErrorNumber, NotSupportedError
from libvirtpy.rpc.options import ConnectionOptions
from libvirtpy.rpc.sasl import SaslCredentials
from libvirtpy.rpc.subscription import (
    DEFAULT_MAX_EVENTS,
    AsyncSubscription,
    Subscription,
)

__all__ = ["AsyncClientBase", "SyncClientBase"]

T = TypeVar("T")
SyncSelf = TypeVar("SyncSelf", bound="SyncClientBase")
AsyncSelf = TypeVar("AsyncSelf", bound="AsyncClientBase")


@runtime_checkable
class SubscribingTransport(Protocol):
    """A transport that can deliver events (the one of a real daemon)."""

    def subscribe(
        self,
        source: str,
        kinds: Iterable[IntEnum] | None,
        target: object,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> Subscription:
        """Start receiving events.

        :param source: the event source.
        :param kinds: the event kinds, or ``None`` for lifecycle events.
        :param target: one object to limit to, or ``None``.
        :param max_events: the most events kept for a slow reader.
        :returns: the subscription.
        """


@runtime_checkable
class AsyncSubscribingTransport(Protocol):
    """An async transport that can deliver events."""

    async def subscribe(
        self,
        source: str,
        kinds: Iterable[IntEnum] | None,
        target: object,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> AsyncSubscription:
        """Start receiving events.

        :param source: the event source.
        :param kinds: the event kinds, or ``None`` for lifecycle events.
        :param target: one object to limit to, or ``None``.
        :param max_events: the most events kept for a slow reader.
        :returns: the subscription.
        """


class SyncClientBase:
    """Connection handling of ``LibvirtClient``."""

    def __init__(self, transport: Transport) -> None:
        """Create a client over a transport.

        :param transport: sends the requests; ``FakeLibvirt`` in the prototype.
        """
        self._transport = transport

    @classmethod
    def open(
        cls: type[SyncSelf],
        uri: str,
        *,
        read_only: bool = False,
        sasl: SaslCredentials | None = None,
        timeout: float | None = None,
        keepalive_interval: float | None = 5.0,
        keepalive_count: int = 5,
        reconnect: bool = False,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 1.0,
    ) -> SyncSelf:
        """Connect to a libvirt daemon, on this machine or another host.

        :param uri: a libvirt URI such as ``qemu:///system`` or
            ``qemu+ssh://user@host/system``.
        :param read_only: use the read-only sockets.
        :param sasl: the user name and password, if the daemon asks for SASL.
        :param timeout: seconds a call may wait for its reply; ``None`` waits as long as
            it takes. A call that times out raises ``CallTimeoutError``; the
            connection stays usable.
        :param keepalive_interval: seconds of silence before the client pings the
            daemon; ``None`` turns the keepalive off.
        :param keepalive_count: unanswered pings after which the connection is given
            up (waiting calls fail with ``ConnectionLostError``).
        :param reconnect: open a lost connection again: the next call, and the
            event subscriptions, continue on a new connection. A call that was
            running when the connection broke still fails, and a stream is lost.
        :param reconnect_attempts: how many times to try before giving up.
        :param reconnect_delay: seconds before the second attempt; each further
            wait doubles (at most 30 seconds). The first attempt is immediate.
        :returns: the client.
        :raises ConnectionError: if the daemon cannot be reached.
        :raises AuthFailedError: if the authentication fails.
        """
        options = ConnectionOptions(
            timeout,
            keepalive_interval,
            keepalive_count,
            reconnect_attempts if reconnect else 0,
            reconnect_delay,
        )
        return cls(
            WireTransport.from_uri(uri, read_only=read_only, sasl=sasl, options=options)
        )

    def events(
        self,
        source: str = "domain",
        kinds: Iterable[IntEnum] | None = None,
        *,
        target: object = None,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> Subscription:
        """Start receiving events from the daemon.

        Iterate the result (or call ``get``) and close it when done::

            with client.events("domain", target="vm") as events:
                for event in events:
                    print(event.kind, event.lifecycle)

        :param source: ``domain``, ``network``, ``pool``, ``node_device`` or ``secret``.
        :param kinds: the event kinds, members of ``DomainEventKind``,
            ``NetworkEventKind``, ...; ``None`` for the ``LIFECYCLE`` events only.
        :param target: limit to one object, as a reference (name, UUID or model);
            ``None`` for all of them.
        :param max_events: the most events kept while you are not reading; a slower
            reader loses the oldest ones, counted in ``subscription.dropped``.
        :returns: the subscription.
        :raises NotSupportedError: if the client is not connected to a real daemon.
        :raises ValueError: if the source or a kind is unknown.
        """
        transport = self._transport
        if not isinstance(transport, SubscribingTransport):
            raise NotSupportedError(
                "events need a connection to a libvirt daemon",
                code=ErrorNumber.NO_SUPPORT,
            )
        return transport.subscribe(source, kinds, target, max_events)

    def close(self) -> None:
        """Close the connection."""
        self._transport.close()

    def __enter__(self: SyncSelf) -> SyncSelf:
        """Use the client in a ``with`` block.

        :returns: the client.
        """
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client when the ``with`` block ends.

        :param exception_type: the exception class, if the block raised.
        :param exception: the exception, if the block raised.
        :param traceback: its traceback, if the block raised.
        """
        self.close()

    def _run(self, operation: Operation[T]) -> T:
        """Run an operation over the transport.

        :param operation: the operation to run.
        :returns: its result.
        """
        return run_sync(operation, self._transport.call)


class AsyncClientBase:
    """Connection handling of ``AsyncLibvirtClient``."""

    def __init__(self, transport: AsyncTransport) -> None:
        """Create a client over a transport.

        :param transport: sends the requests; ``AsyncFakeTransport`` in the prototype.
        """
        self._transport = transport

    @classmethod
    async def open(
        cls: type[AsyncSelf],
        uri: str,
        *,
        read_only: bool = False,
        sasl: SaslCredentials | None = None,
        timeout: float | None = None,
        keepalive_interval: float | None = 5.0,
        keepalive_count: int = 5,
        reconnect: bool = False,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 1.0,
    ) -> AsyncSelf:
        """Connect to a libvirt daemon, on this machine or another host.

        :param uri: a libvirt URI such as ``qemu:///system`` or
            ``qemu+ssh://user@host/system``.
        :param read_only: use the read-only sockets.
        :param sasl: the user name and password, if the daemon asks for SASL.
        :param timeout: seconds a call may wait for its reply; ``None`` waits as long as
            it takes. A call that times out raises ``CallTimeoutError``; the
            connection stays usable.
        :param keepalive_interval: seconds of silence before the client pings the
            daemon; ``None`` turns the keepalive off.
        :param keepalive_count: unanswered pings after which the connection is given
            up (waiting calls fail with ``ConnectionLostError``).
        :param reconnect: open a lost connection again: the next call, and the
            event subscriptions, continue on a new connection. A call that was
            running when the connection broke still fails, and a stream is lost.
        :param reconnect_attempts: how many times to try before giving up.
        :param reconnect_delay: seconds before the second attempt; each further
            wait doubles (at most 30 seconds). The first attempt is immediate.
        :returns: the client.
        :raises ConnectionError: if the daemon cannot be reached.
        :raises AuthFailedError: if the authentication fails.
        """
        options = ConnectionOptions(
            timeout,
            keepalive_interval,
            keepalive_count,
            reconnect_attempts if reconnect else 0,
            reconnect_delay,
        )
        transport = await AsyncWireTransport.from_uri(
            uri, read_only=read_only, sasl=sasl, options=options
        )
        return cls(transport)

    async def events(
        self,
        source: str = "domain",
        kinds: Iterable[IntEnum] | None = None,
        *,
        target: object = None,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> AsyncSubscription:
        """Start receiving events from the daemon.

        Iterate the result with ``async for`` and close it when done::

            async with await client.events("domain", target="vm") as events:
                async for event in events:
                    print(event.kind, event.lifecycle)

        :param source: ``domain``, ``network``, ``pool``, ``node_device`` or ``secret``.
        :param kinds: the event kinds, members of ``DomainEventKind``,
            ``NetworkEventKind``, ...; ``None`` for the ``LIFECYCLE`` events only.
        :param target: limit to one object, as a reference (name, UUID or model);
            ``None`` for all of them.
        :param max_events: the most events kept while you are not reading; a slower
            reader loses the oldest ones, counted in ``subscription.dropped``.
        :returns: the subscription.
        :raises NotSupportedError: if the client is not connected to a real daemon.
        :raises ValueError: if the source or a kind is unknown.
        """
        transport = self._transport
        if not isinstance(transport, AsyncSubscribingTransport):
            raise NotSupportedError(
                "events need a connection to a libvirt daemon",
                code=ErrorNumber.NO_SUPPORT,
            )
        return await transport.subscribe(source, kinds, target, max_events)

    async def close(self) -> None:
        """Close the connection."""
        await self._transport.close()

    async def __aenter__(self: AsyncSelf) -> AsyncSelf:
        """Use the client in an ``async with`` block.

        :returns: the client.
        """
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client when the ``async with`` block ends.

        :param exception_type: the exception class, if the block raised.
        :param exception: the exception, if the block raised.
        :param traceback: its traceback, if the block raised.
        """
        await self.close()

    async def _run(self, operation: Operation[T]) -> T:
        """Run an operation over the transport.

        :param operation: the operation to run.
        :returns: its result.
        """
        return await run_async(operation, self._transport.call)
