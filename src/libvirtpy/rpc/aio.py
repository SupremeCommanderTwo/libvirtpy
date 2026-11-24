"""An asyncio connection to one libvirt daemon socket.

A background task reads replies, so many calls may be in flight at once; each
caller awaits the future of its own serial.
"""

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol, TypeVar

from libvirtpy.rpc.options import ConnectionOptions
from libvirtpy.rpc.procedure import Procedure
from libvirtpy.rpc.session import (
    CallTimeoutError,
    Completed,
    ConnectionLostError,
    ProtocolError,
    ServerEvent,
    Session,
    StreamEvent,
)

__all__ = ["AsyncRpc"]

RECEIVE_SIZE = 65536


class StreamSink(Protocol):
    """Where the data of an open stream is delivered."""

    serial: int

    def deliver(self, event: StreamEvent) -> None:
        """Receive what the connection read for the stream.

        :param event: the data, the end, or the error.
        """


OnResult = Callable[[Any], None]
EventListener = Callable[[ServerEvent], None]
SelfT = TypeVar("SelfT", bound="AsyncRpc")


class AsyncRpc:
    """Calls procedures of one daemon; calls may overlap."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        on_close: Callable[[], Awaitable[None]] | None = None,
        options: ConnectionOptions | None = None,
    ) -> None:
        """Wrap a connected pair of streams and start reading.

        :param reader: the receiving side.
        :param writer: the sending side.
        :param on_close: awaited when the connection closes, e.g. to end the
            ``ssh`` process behind the streams.
        :param options: the call timeout and the keepalive; the defaults if left out.
        """
        self._options = options or ConnectionOptions()
        self._last_received = time.monotonic()
        self._reader = reader
        self._writer = writer
        self._on_close = on_close

        self._session = Session()
        self._waiting: dict[int, asyncio.Future[Completed]] = {}
        self._on_result: dict[int, OnResult] = {}

        self._listeners: dict[int, EventListener] = {}
        self._on_lost: list[Callable[[Exception], None]] = []
        self._failure: Exception | None = None
        self._streams: dict[int, StreamSink] = {}

        loop = asyncio.get_running_loop()
        self._reading = loop.create_task(self._read_loop())
        self._watching: asyncio.Task[None] | None = None
        if self._options.keepalive_interval is not None:
            self._watching = loop.create_task(self._keepalive_loop())

    @classmethod
    async def connect_unix(
        cls: type[SelfT], path: Path | str, options: ConnectionOptions | None = None
    ) -> SelfT:
        """Connect to a daemon's UNIX socket.

        :param path: the socket file, e.g. ``/run/libvirt/virtqemud-sock``.
        :param options: the call timeout and the keepalive.
        :returns: the connection.
        :raises OSError: if the socket cannot be reached.
        """
        reader, writer = await asyncio.open_unix_connection(str(path))
        return cls(reader, writer, options=options)

    async def call(
        self,
        procedure: Procedure[Any, Any],
        args: Any = None,
        *,
        on_result: OnResult | None = None,
        stream: StreamSink | None = None,
    ) -> Any:
        """Call a procedure and wait for its reply.

        :param procedure: the procedure.
        :param args: its arguments struct, or ``None`` if it has none.
        :param on_result: called with the result as soon as the reply is read,
            before anything the daemon sent after it is handled; a subscription
            uses it to listen from the first event.
        :param stream: for a call that opens a data stream: where its data goes.
            The call's serial becomes ``stream.serial`` before it is sent.
        :returns: the return struct, or ``None`` if the procedure returns nothing.
        :raises LibvirtError: if the daemon reports an error.
        :raises ConnectionLostError: if the connection ended.
        :raises CallTimeoutError: if there was no reply within the call timeout.
        """
        if self._failure is not None:
            raise self._failure

        serial, packet = self._session.call(procedure, args, stream=stream is not None)
        if stream is not None:
            stream.serial = serial
            self._streams[serial] = stream
        future: asyncio.Future[Completed] = asyncio.get_running_loop().create_future()
        self._waiting[serial] = future
        if on_result is not None:
            self._on_result[serial] = on_result

        self._writer.write(packet)
        await self._writer.drain()

        completed = await self._wait(future, serial, procedure, stream)
        if completed.error is not None:
            if stream is not None:
                self._streams.pop(stream.serial, None)
            raise completed.error
        return completed.result

    async def send_stream_data(self, serial: int, data: bytes) -> None:
        """Send data on an open stream.

        :param serial: the stream.
        :param data: the bytes.
        """
        await self._write(self._session.stream_data(serial, data))

    async def finish_stream(self, serial: int) -> None:
        """Tell the daemon that we have sent everything on a stream.

        :param serial: the stream.
        """
        await self._write(self._session.stream_finish(serial))

    async def abort_stream(self, serial: int) -> None:
        """Give up on a stream.

        :param serial: the stream.
        """
        packet = self._session.stream_abort(serial)
        self._streams.pop(serial, None)
        await self._write(packet)

    @property
    def failure(self) -> Exception | None:
        """Why the connection ended.

        :returns: the error, or ``None`` while the connection is alive.
        """
        return self._failure

    def add_listener(self, callback_id: int, listener: EventListener) -> None:
        """Send the events of a subscription to ``listener``.

        :param callback_id: the id the daemon gave the subscription.
        :param listener: called with each ``ServerEvent``, in the event loop.
        """
        self._listeners[callback_id] = listener

    def remove_listener(self, callback_id: int) -> None:
        """Stop sending the events of a subscription.

        :param callback_id: the id the daemon gave the subscription.
        """
        self._listeners.pop(callback_id, None)

    def when_lost(self, callback: Callable[[Exception], None]) -> None:
        """Call ``callback`` when the connection ends.

        :param callback: called with the reason, in the event loop.
        """
        if self._failure is not None:
            callback(self._failure)
            return
        self._on_lost.append(callback)

    async def close(self) -> None:
        """Close the connection and stop reading."""
        self._reading.cancel()
        if self._watching is not None:
            self._watching.cancel()
        self._writer.close()
        with contextlib.suppress(OSError):
            await self._writer.wait_closed()

        self._fail_waiting(ConnectionLostError("the connection was closed"))
        if self._on_close is not None:
            await self._on_close()

    async def __aenter__(self: SelfT) -> SelfT:
        """Use the connection in an ``async with`` block.

        :returns: the connection.
        """
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the connection when the block ends.

        :param exception_type: the exception class, if the block raised.
        :param exception: the exception, if the block raised.
        :param traceback: its traceback, if the block raised.
        """
        await self.close()

    async def _wait(
        self,
        future: asyncio.Future[Completed],
        serial: int,
        procedure: Procedure[Any, Any],
        stream: StreamSink | None,
    ) -> Completed:
        """Wait for the reply of a call, for at most the call timeout.

        A call that is cancelled or times out is abandoned: its late reply is dropped
        instead of being taken for a protocol error.

        :param future: completed by the reading task.
        :param serial: the call.
        :param procedure: the procedure, for the message.
        :param stream: the stream the call opens, if any.
        :returns: the outcome.
        :raises CallTimeoutError: if no reply came in time.
        """
        timeout = self._options.call_timeout
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout)
        except (TimeoutError, asyncio.CancelledError) as error:
            self._waiting.pop(serial, None)
            self._on_result.pop(serial, None)
            self._session.abandon(serial)

            if stream is not None:
                self._streams.pop(serial, None)
            future.cancel()

            if isinstance(error, asyncio.CancelledError):
                raise
            raise CallTimeoutError(
                f"no reply to {procedure.name} within {timeout} seconds"
            ) from None

    async def _keepalive_loop(self) -> None:
        """Ping the daemon when it is silent, and give up on one that stays silent."""
        interval = self._options.keepalive_interval
        limit = self._options.dead_after
        assert interval is not None and limit is not None

        while True:
            await asyncio.sleep(interval / 2)
            silent_for = time.monotonic() - self._last_received
            if silent_for >= limit:
                self._fail_waiting(
                    ConnectionLostError(
                        f"the daemon has been silent for {silent_for:.0f} seconds"
                    )
                )
                self._writer.close()
                return
            if silent_for >= interval:
                try:
                    await self._write(self._session.keepalive_ping())
                except OSError as error:
                    self._fail_waiting(ConnectionLostError(f"cannot send: {error}"))
                    return

    async def _read_loop(self) -> None:
        """Feed received bytes to the session and wake the callers."""
        try:
            while True:
                data = await self._reader.read(RECEIVE_SIZE)
                if not data:
                    raise ConnectionLostError("the daemon closed the connection")
                self._last_received = time.monotonic()
                self._deliver(self._session.feed(data))

                self._dispatch_events(self._session.take_events())
                self._dispatch_stream(self._session.take_stream_events())
                await self._send_pending()
        except (ProtocolError, OSError) as error:
            self._fail_waiting(error)

    def _deliver(self, completed: list[Completed]) -> None:
        """Hand finished calls to the callers waiting for them.

        :param completed: the outcomes, from the session.
        """
        for item in completed:
            future = self._waiting.pop(item.serial, None)
            on_result = self._on_result.pop(item.serial, None)
            if on_result is not None and item.error is None:
                on_result(item.result)
            if future is not None and not future.done():
                future.set_result(item)

    async def _write(self, packet: bytes) -> None:
        """Send a packet, if there is one.

        :param packet: the bytes; empty means nothing to send.
        """
        if packet:
            self._writer.write(packet)
            await self._writer.drain()

    def _dispatch_stream(self, events: list[StreamEvent]) -> None:
        """Give each stream event to its stream.

        :param events: what the session decoded for the open streams.
        """
        for event in events:
            sink = self._streams.get(event.serial)
            if event.kind in ("closed", "error"):
                self._streams.pop(event.serial, None)
            if sink is not None:
                sink.deliver(event)

    def _dispatch_events(self, events: list[ServerEvent]) -> None:
        """Give each event to the listener of its subscription.

        :param events: the events the session decoded.
        """
        for event in events:
            callback_id = getattr(event.message, "callback_id", None)
            listener = (
                self._listeners.get(callback_id) if callback_id is not None else None
            )
            if listener is not None:
                listener(event)

    async def _send_pending(self) -> None:
        """Send what the session queued by itself (keepalive pongs)."""
        pending = self._session.take_outgoing()
        if pending:
            self._writer.write(pending)
            await self._writer.drain()

    def _fail_waiting(self, error: Exception) -> None:
        """Make every waiting call fail.

        :param error: the reason.
        """
        if self._failure is None:
            self._failure = error
        for future in self._waiting.values():
            if not future.done():
                future.set_exception(error)
        self._waiting.clear()
        self._on_result.clear()

        sinks, self._streams = self._streams, {}
        for serial, sink in sinks.items():
            sink.deliver(StreamEvent(serial, "error", error=error))

        lost, self._on_lost = self._on_lost, []
        for callback in lost:
            callback(error)
