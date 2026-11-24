"""A blocking connection to one libvirt daemon socket."""

import contextlib
import socket
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future
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

__all__ = ["SocketStream", "Stream", "SyncRpc"]

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
SelfT = TypeVar("SelfT", bound="SyncRpc")


class Stream(Protocol):
    """A connected byte stream: a socket, a TLS socket, or an ``ssh`` process."""

    def send(self, data: bytes) -> None:
        """Send all of ``data``.

        :param data: the bytes.
        """

    def receive(self) -> bytes:
        """Wait for bytes.

        :returns: some bytes, or nothing if the other side closed.
        """

    def close(self) -> None:
        """Close the stream."""


class SocketStream:
    """A ``Stream`` over a connected socket (plain or TLS)."""

    def __init__(self, connection: socket.socket) -> None:
        """Wrap a socket.

        :param connection: a connected stream socket.
        """
        self._socket = connection

    def send(self, data: bytes) -> None:
        """Send all of ``data``.

        :param data: the bytes.
        """
        self._socket.sendall(data)

    def receive(self) -> bytes:
        """Wait for bytes.

        :returns: some bytes, or nothing if the other side closed.
        """
        return self._socket.recv(RECEIVE_SIZE)

    def close(self) -> None:
        """Close the socket, waking a thread that waits to read from it."""
        with contextlib.suppress(OSError):
            self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()


class SyncRpc:
    """Calls procedures of one daemon; calls from several threads may overlap.

    A thread reads everything the daemon sends: replies wake the call that waits
    for them, events go to the listeners, and keepalive pings are answered even
    while no call is running.
    """

    def __init__(
        self, stream: Stream, options: ConnectionOptions | None = None
    ) -> None:
        """Wrap a connected stream and start reading it.

        :param stream: a stream to a libvirt daemon.
        :param options: the call timeout and the keepalive; the defaults if left out.
        """
        self._stream = stream
        self._options = options or ConnectionOptions()
        self._last_received = time.monotonic()
        self._stopped = threading.Event()

        self._session = Session()
        self._state = threading.Lock()
        self._send = threading.Lock()

        self._waiting: dict[int, tuple[Future[Completed], OnResult | None]] = {}
        self._listeners: dict[int, EventListener] = {}
        self._on_lost: list[Callable[[Exception], None]] = []
        self._failure: Exception | None = None
        self._streams: dict[int, StreamSink] = {}

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        if self._options.keepalive_interval is not None:
            threading.Thread(target=self._keepalive_loop, daemon=True).start()

    @classmethod
    def connect_unix(
        cls: type[SelfT], path: Path | str, options: ConnectionOptions | None = None
    ) -> SelfT:
        """Connect to a daemon's UNIX socket.

        :param path: the socket file, e.g. ``/run/libvirt/virtqemud-sock``.
        :param options: the call timeout and the keepalive.
        :returns: the connection.
        :raises OSError: if the socket cannot be reached.
        """
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            connection.connect(str(path))
        except OSError:
            connection.close()
            raise
        return cls(SocketStream(connection), options)

    def call(
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
        :param on_result: called with the result by the reading thread as soon as
            the reply arrives, before it handles anything the daemon sent after
            it; a subscription uses it to listen from the first event.
        :param stream: for a call that opens a data stream: where its data goes.
            The call's serial becomes ``stream.serial`` before it is sent.
        :returns: the return struct, or ``None`` if the procedure returns nothing.
        :raises LibvirtError: if the daemon reports an error.
        :raises ConnectionLostError: if the connection ended.
        :raises CallTimeoutError: if there was no reply within the call timeout.
        """
        future: Future[Completed] = Future()
        with self._state:
            if self._failure is not None:
                raise self._failure
            serial, packet = self._session.call(
                procedure, args, stream=stream is not None
            )
            self._waiting[serial] = (future, on_result)
            if stream is not None:
                stream.serial = serial
                self._streams[serial] = stream

        self._send_bytes(packet)
        completed = self._wait(future, serial, procedure, stream)
        if completed.error is not None:
            self._forget_stream(stream)
            raise completed.error
        return completed.result

    def send_stream_data(self, serial: int, data: bytes) -> None:
        """Send data on an open stream.

        :param serial: the stream.
        :param data: the bytes.
        """
        with self._state:
            packet = self._session.stream_data(serial, data)
        if packet:
            self._send_bytes(packet)

    def finish_stream(self, serial: int) -> None:
        """Tell the daemon that we have sent everything on a stream.

        :param serial: the stream.
        """
        with self._state:
            packet = self._session.stream_finish(serial)
        if packet:
            self._send_bytes(packet)

    def abort_stream(self, serial: int) -> None:
        """Give up on a stream.

        :param serial: the stream.
        """
        with self._state:
            packet = self._session.stream_abort(serial)
            self._streams.pop(serial, None)
        if packet:
            self._send_bytes(packet)

    @property
    def failure(self) -> Exception | None:
        """Why the connection ended.

        :returns: the error, or ``None`` while the connection is alive.
        """
        return self._failure

    def add_listener(self, callback_id: int, listener: EventListener) -> None:
        """Send the events of a subscription to ``listener``.

        :param callback_id: the id the daemon gave the subscription.
        :param listener: called in the reading thread with each ``ServerEvent``.
        """
        with self._state:
            self._listeners[callback_id] = listener

    def remove_listener(self, callback_id: int) -> None:
        """Stop sending the events of a subscription.

        :param callback_id: the id the daemon gave the subscription.
        """
        with self._state:
            self._listeners.pop(callback_id, None)

    def when_lost(self, callback: Callable[[Exception], None]) -> None:
        """Call ``callback`` when the connection ends.

        :param callback: called in the reading thread with the reason.
        """
        with self._state:
            lost = self._failure
            if lost is None:
                self._on_lost.append(callback)
        if lost is not None:
            callback(lost)

    def close(self) -> None:
        """Close the connection; waiting calls and subscriptions end."""
        self._stream.close()
        self._fail(ConnectionLostError("the connection was closed"))
        if threading.current_thread() is not self._reader:
            self._reader.join(timeout=5)

    def __enter__(self: SelfT) -> SelfT:
        """Use the connection in a ``with`` block.

        :returns: the connection.
        """
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the connection when the ``with`` block ends.

        :param exception_type: the exception class, if the block raised.
        :param exception: the exception, if the block raised.
        :param traceback: its traceback, if the block raised.
        """
        self.close()

    def _keepalive_loop(self) -> None:
        """Ping the daemon when it is silent, and give up on one that stays silent."""
        interval = self._options.keepalive_interval
        limit = self._options.dead_after
        assert interval is not None and limit is not None

        while not self._stopped.wait(interval / 2):
            silent_for = time.monotonic() - self._last_received
            if silent_for >= limit:
                self._fail(
                    ConnectionLostError(
                        f"the daemon has been silent for {silent_for:.0f} seconds"
                    )
                )
                return
            if silent_for >= interval:
                try:
                    with self._state:
                        packet = self._session.keepalive_ping()
                    self._send_bytes(packet)
                except ConnectionLostError as error:
                    self._fail(error)
                    return

    def _wait(
        self,
        future: Future[Completed],
        serial: int,
        procedure: Procedure[Any, Any],
        stream: StreamSink | None,
    ) -> Completed:
        """Wait for the reply of a call, for at most the call timeout.

        :param future: completed by the reading thread.
        :param serial: the call.
        :param procedure: the procedure, for the message.
        :param stream: the stream the call opens, if any.
        :returns: the outcome.
        :raises CallTimeoutError: if no reply came in time.
        """
        timeout = self._options.call_timeout
        try:
            return future.result(timeout)
        except TimeoutError:
            if not future.done():
                with self._state:
                    self._waiting.pop(serial, None)
                    self._session.abandon(serial)
                self._forget_stream(stream)
                raise CallTimeoutError(
                    f"no reply to {procedure.name} within {timeout} seconds"
                ) from None
            return future.result()

    def _read_loop(self) -> None:
        """Read from the daemon until the connection ends."""
        while True:
            try:
                data = self._stream.receive()
            except (OSError, ValueError) as error:
                self._fail(ConnectionLostError(f"the connection broke: {error}"))
                return
            if not data:
                self._fail(ConnectionLostError("the daemon closed the connection"))
                return
            self._last_received = time.monotonic()

            try:
                self._handle(data)
            except (ProtocolError, OSError) as error:
                self._fail(error)
                return

    def _handle(self, data: bytes) -> None:
        """Process received bytes: finish calls, deliver events, answer pings.

        :param data: bytes from the daemon.
        """
        with self._state:
            completed = self._session.feed(data)
            events = self._session.take_events()
            stream_events = self._session.take_stream_events()
            pending = self._session.take_outgoing()

            ready = [(self._waiting.pop(item.serial), item) for item in completed]
            listeners = dict(self._listeners)
            sinks = dict(self._streams)
            self._forget_finished(stream_events)

        if pending:
            self._send_bytes(pending)
        for (future, on_result), item in ready:
            if on_result is not None and item.error is None:
                on_result(item.result)
            future.set_result(item)
        for event in events:
            self._deliver(listeners, event)
        for stream_event in stream_events:
            sink = sinks.get(stream_event.serial)
            if sink is not None:
                sink.deliver(stream_event)

    def _deliver(self, listeners: dict[int, EventListener], event: ServerEvent) -> None:
        """Give an event to the listener of its subscription.

        :param listeners: the listeners by subscription id.
        :param event: the event.
        """
        callback_id = getattr(event.message, "callback_id", None)
        listener = listeners.get(callback_id) if callback_id is not None else None
        if listener is not None:
            listener(event)

    def _forget_finished(self, events: list[StreamEvent]) -> None:
        """Stop expecting data for the streams that ended.

        Call with the state lock held.

        :param events: the stream events just decoded.
        """
        for event in events:
            if event.kind in ("closed", "error"):
                self._streams.pop(event.serial, None)

    def _forget_stream(self, stream: StreamSink | None) -> None:
        """Stop expecting data for a stream whose call failed.

        :param stream: the stream, or ``None``.
        """
        if stream is not None:
            with self._state:
                self._streams.pop(stream.serial, None)

    def _send_bytes(self, data: bytes) -> None:
        """Send bytes, one sender at a time.

        :param data: what to send.
        :raises ConnectionLostError: if the connection is gone.
        """
        try:
            with self._send:
                self._stream.send(data)
        except OSError as error:
            raise ConnectionLostError(f"cannot send: {error}") from error

    def _fail(self, error: Exception) -> None:
        """End the connection: fail the waiting calls and tell the subscriptions.

        :param error: why it ended.
        """
        with self._state:
            if self._failure is not None:
                return
            self._failure = error
            self._stopped.set()

            waiting = list(self._waiting.values())
            self._waiting.clear()

            lost = list(self._on_lost)
            self._on_lost.clear()

            sinks = list(self._streams.items())
            self._streams.clear()

        for serial, sink in sinks:
            sink.deliver(StreamEvent(serial, "error", error=error))
        for future, _ in waiting:
            future.set_exception(error)
        for callback in lost:
            callback(error)
