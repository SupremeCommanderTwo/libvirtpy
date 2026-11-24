"""Event subscriptions: iterate over the events the daemon pushes.

``Subscription`` (blocking) and ``AsyncSubscription`` are made by
``client.events(...)``. Iterate them, or call ``get``; close them (or use them in
a ``with`` block) to tell the daemon to stop sending::

    with client.events("domain", target="vm") as events:
        for event in events:
            print(event.kind, event.lifecycle)
"""

import asyncio
import contextlib
import threading
import time
from collections import deque
from types import TracebackType
from typing import Any, TypeVar

from libvirtpy.rpc.aio import AsyncRpc
from libvirtpy.rpc.errors import LibvirtError
from libvirtpy.rpc.events import Event, make_event
from libvirtpy.rpc.procedure import Procedure
from libvirtpy.rpc.session import ProtocolError, ServerEvent
from libvirtpy.rpc.sync import SyncRpc

__all__ = ["DEFAULT_MAX_EVENTS", "AsyncSubscription", "EventBuffer", "Subscription"]

DEFAULT_MAX_EVENTS = 10_000

SyncSelf = TypeVar("SyncSelf", bound="Subscription")
AsyncSelf = TypeVar("AsyncSelf", bound="AsyncSubscription")


class _End:
    """Marks the end of the events in a queue."""


END = _End()
QueueItem = Event | Exception | _End


class EventBuffer:
    """The events waiting for the reader: at most ``capacity``, newest kept.

    A reader that is slower than the daemon cannot make memory grow without end: when
    the buffer is full the oldest event is dropped and ``dropped`` counts it. The end
    of the subscription (closed, or the connection lost) is kept after the events and
    stays: once reached, every read gets it again.
    """

    def __init__(self, capacity: int) -> None:
        """Create an empty buffer.

        :param capacity: the most events kept; at least 1.
        :raises ValueError: if the capacity is not positive.
        """
        if capacity < 1:
            raise ValueError("max_events must be at least 1")
        self.dropped = 0
        """How many events were dropped because the reader was too slow."""

        self._capacity = capacity
        self._events: deque[Event] = deque()
        self._final: Exception | _End | None = None

    def add(self, event: Event) -> None:
        """Keep an event, dropping the oldest if the buffer is full.

        :param event: the event.
        """
        if len(self._events) >= self._capacity:
            self._events.popleft()
            self.dropped += 1
        self._events.append(event)

    def finish(self, final: Exception | _End) -> None:
        """Mark the end: the first one wins.

        :param final: ``END``, or the error that ended the subscription.
        """
        if self._final is None:
            self._final = final

    def ready(self) -> bool:
        """Tell whether a read would find something.

        :returns: ``True`` if there is an event or an end.
        """
        return bool(self._events) or self._final is not None

    def take(self) -> QueueItem:
        """Take the next event, or the end.

        :returns: an event; or the end, which is not consumed.
        :raises LookupError: if the buffer is empty and not finished.
        """
        if self._events:
            return self._events.popleft()
        if self._final is None:
            raise LookupError("nothing to take")
        return self._final


class Subscription:
    """Events from one daemon, delivered to a blocking reader."""

    def __init__(
        self,
        rpc: SyncRpc,
        deregister: Procedure[Any, Any],
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> None:
        """Create a subscription that has no events registered yet.

        :param rpc: the connection the events arrive on.
        :param deregister: the procedure that ends one registration.
        :param max_events: the most events kept for a slow reader; older ones are
            dropped and counted in ``dropped``.
        """
        self._rpc = rpc
        self._deregister = deregister
        self._buffer = EventBuffer(max_events)
        self._ready = threading.Condition()

        self._ids: list[int] = []
        self._closed = False
        self._reconnects = 0

    def attach(self, callback_id: int) -> None:
        """Start listening to a registration the daemon made for us.

        :param callback_id: the id the daemon gave.
        """
        self._ids.append(callback_id)
        self._rpc.add_listener(callback_id, self._deliver)

    @property
    def dropped(self) -> int:
        """How many events were dropped because the reader was too slow.

        :returns: the count.
        """
        return self._buffer.dropped

    @property
    def reconnects(self) -> int:
        """How many times the subscription was registered again after a reconnect.

        Events that the daemon sent while the connection was down are lost.

        :returns: the count.
        """
        return self._reconnects

    def rebind(self, rpc: SyncRpc) -> bool:
        """Move to a new connection; the caller registers the events again.

        :param rpc: the new connection.
        :returns: ``False`` if the subscription was closed meanwhile.
        """
        if self._closed:
            return False
        self._rpc = rpc
        self._ids = []
        self._reconnects += 1
        return True

    def lost(self, error: Exception) -> None:
        """Tell the reader that the connection ended.

        :param error: why it ended.
        """
        self._finish(error)

    def get(self, timeout: float | None = None) -> Event:
        """Wait for the next event.

        :param timeout: seconds to wait; ``None`` to wait for ever.
        :returns: the event.
        :raises TimeoutError: if none came in time.
        :raises StopIteration: if the subscription was closed.
        :raises ConnectionLostError: if the connection ended.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._ready:
            while not self._buffer.ready():
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise TimeoutError("no event arrived in time")
                self._ready.wait(remaining)
            item = self._buffer.take()

        if isinstance(item, Exception):
            raise item
        if isinstance(item, _End):
            raise StopIteration
        return item

    def close(self) -> None:
        """Stop the subscription: the daemon stops sending, iteration ends."""
        if self._closed:
            return
        self._closed = True

        for callback_id in self._ids:
            self._rpc.remove_listener(callback_id)
            self._deregister_one(callback_id)
        self._finish(END)

    def __iter__(self: SyncSelf) -> SyncSelf:
        """Iterate over the events until the subscription is closed.

        :returns: the subscription.
        """
        return self

    def __next__(self) -> Event:
        """Wait for the next event.

        :returns: the event.
        :raises StopIteration: when the subscription is closed.
        :raises ConnectionLostError: if the connection ended.
        """
        return self.get()

    def __enter__(self: SyncSelf) -> SyncSelf:
        """Use the subscription in a ``with`` block.

        :returns: the subscription.
        """
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the subscription when the block ends.

        :param exception_type: the exception class, if the block raised.
        :param exception: the exception, if the block raised.
        :param traceback: its traceback, if the block raised.
        """
        self.close()

    def _deliver(self, server_event: ServerEvent) -> None:
        """Queue an event pushed by the daemon.

        :param server_event: the decoded message.
        """
        event = make_event(server_event)
        if event is not None:
            with self._ready:
                self._buffer.add(event)
                self._ready.notify_all()

    def _finish(self, final: Exception | _End) -> None:
        """Mark the end of the events and wake the reader.

        :param final: ``END``, or the error that ended the subscription.
        """
        with self._ready:
            self._buffer.finish(final)
            self._ready.notify_all()

    def _deregister_one(self, callback_id: int) -> None:
        """Tell the daemon to stop one registration; it may be gone already.

        :param callback_id: the registration.
        """
        args = self._deregister.args
        assert args is not None
        with contextlib.suppress(LibvirtError, ProtocolError):
            self._rpc.call(self._deregister, args(callback_id=callback_id))


class AsyncSubscription:
    """Events from one daemon, delivered to an ``async for`` loop."""

    def __init__(
        self,
        rpc: AsyncRpc,
        deregister: Procedure[Any, Any],
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> None:
        """Create a subscription that has no events registered yet.

        :param rpc: the connection the events arrive on.
        :param deregister: the procedure that ends one registration.
        :param max_events: the most events kept for a slow reader; older ones are
            dropped and counted in ``dropped``.
        """
        self._rpc = rpc
        self._deregister = deregister
        self._buffer = EventBuffer(max_events)
        self._wake = asyncio.Event()

        self._ids: list[int] = []
        self._closed = False
        self._reconnects = 0

    def attach(self, callback_id: int) -> None:
        """Start listening to a registration the daemon made for us.

        :param callback_id: the id the daemon gave.
        """
        self._ids.append(callback_id)
        self._rpc.add_listener(callback_id, self._deliver)

    @property
    def dropped(self) -> int:
        """How many events were dropped because the reader was too slow.

        :returns: the count.
        """
        return self._buffer.dropped

    @property
    def reconnects(self) -> int:
        """How many times the subscription was registered again after a reconnect.

        Events that the daemon sent while the connection was down are lost.

        :returns: the count.
        """
        return self._reconnects

    def rebind(self, rpc: AsyncRpc) -> bool:
        """Move to a new connection; the caller registers the events again.

        :param rpc: the new connection.
        :returns: ``False`` if the subscription was closed meanwhile.
        """
        if self._closed:
            return False
        self._rpc = rpc
        self._ids = []
        self._reconnects += 1
        return True

    def lost(self, error: Exception) -> None:
        """Tell the reader that the connection ended.

        :param error: why it ended.
        """
        self._finish(error)

    async def get(self, timeout: float | None = None) -> Event:
        """Wait for the next event.

        :param timeout: seconds to wait; ``None`` to wait for ever.
        :returns: the event.
        :raises TimeoutError: if none came in time.
        :raises StopAsyncIteration: if the subscription was closed.
        :raises ConnectionLostError: if the connection ended.
        """
        try:
            await asyncio.wait_for(self._until_ready(), timeout)
        except TimeoutError:
            raise TimeoutError("no event arrived in time") from None
        item = self._buffer.take()

        if isinstance(item, Exception):
            raise item
        if isinstance(item, _End):
            raise StopAsyncIteration
        return item

    async def close(self) -> None:
        """Stop the subscription: the daemon stops sending, iteration ends."""
        if self._closed:
            return
        self._closed = True

        for callback_id in self._ids:
            self._rpc.remove_listener(callback_id)
            await self._deregister_one(callback_id)
        self._finish(END)

    def __aiter__(self: AsyncSelf) -> AsyncSelf:
        """Iterate over the events until the subscription is closed.

        :returns: the subscription.
        """
        return self

    async def __anext__(self) -> Event:
        """Wait for the next event.

        :returns: the event.
        :raises StopAsyncIteration: when the subscription is closed.
        :raises ConnectionLostError: if the connection ended.
        """
        return await self.get()

    async def __aenter__(self: AsyncSelf) -> AsyncSelf:
        """Use the subscription in an ``async with`` block.

        :returns: the subscription.
        """
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the subscription when the block ends.

        :param exception_type: the exception class, if the block raised.
        :param exception: the exception, if the block raised.
        :param traceback: its traceback, if the block raised.
        """
        await self.close()

    def _deliver(self, server_event: ServerEvent) -> None:
        """Queue an event pushed by the daemon.

        :param server_event: the decoded message.
        """
        event = make_event(server_event)
        if event is not None:
            self._buffer.add(event)
            self._wake.set()

    def _finish(self, final: Exception | _End) -> None:
        """Mark the end of the events and wake the reader.

        :param final: ``END``, or the error that ended the subscription.
        """
        self._buffer.finish(final)
        self._wake.set()

    async def _until_ready(self) -> None:
        """Wait until there is an event or an end to read."""
        while not self._buffer.ready():
            self._wake.clear()
            await self._wake.wait()

    async def _deregister_one(self, callback_id: int) -> None:
        """Tell the daemon to stop one registration; it may be gone already.

        :param callback_id: the registration.
        """
        args = self._deregister.args
        assert args is not None
        with contextlib.suppress(LibvirtError, ProtocolError):
            await self._rpc.call(self._deregister, args(callback_id=callback_id))
