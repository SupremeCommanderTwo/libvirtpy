"""Data streams: console, screenshot and volume upload/download.

A stream is the open end of a data channel that a call set up. ``RemoteStream``
is a file-like object (``read``, ``write``, ``close``, ``with``); ``AsyncRemoteStream``
has the same methods as coroutines::

    with client.open_domain_console("vm") as console:
        console.write(b"\\n")
        print(console.read(100))

    with client.download_pool_volume("pool", "disk.img") as source:
        data = source.read()
"""

import asyncio
import contextlib
import io
import queue
from types import TracebackType
from typing import Any, Literal, TypeVar

from libvirtpy.rpc.aio import AsyncRpc
from libvirtpy.rpc.session import StreamEvent
from libvirtpy.rpc.sync import SyncRpc

__all__ = ["AsyncRemoteStream", "Mode", "RemoteStream"]

Mode = Literal["read", "write", "both"]
CHUNK_SIZE = 65536
CLOSE_TIMEOUT_SECONDS = 10
AsyncSelf = TypeVar("AsyncSelf", bound="AsyncRemoteStream")


class RemoteStream(io.RawIOBase):
    """A blocking, file-like stream to or from a daemon."""

    def __init__(self, rpc: SyncRpc, mode: Mode) -> None:
        """Create the stream; the connection sets ``serial`` when the call is sent.

        :param rpc: the connection the stream is on.
        :param mode: ``read`` (data comes from the daemon), ``write`` (data goes to
            it) or ``both`` (a console).
        """
        super().__init__()
        self.mode = mode
        self.serial = -1
        self.reply: Any = None
        """What the call that opened the stream returned (for a screenshot: the
        MIME type)."""

        self._rpc = rpc
        self._events: queue.Queue[StreamEvent] = queue.Queue()
        self._pending = b""
        self._eof = False
        self._dead = False

    def deliver(self, event: StreamEvent) -> None:
        """Receive what the connection read for this stream (reading thread).

        :param event: the data, the end, or the error.
        """
        self._events.put(event)

    def readable(self) -> bool:
        """Tell whether data can be read from the stream.

        :returns: ``True`` for a ``read`` or ``both`` stream.
        """
        return self.mode in ("read", "both")

    def writable(self) -> bool:
        """Tell whether data can be written to the stream.

        :returns: ``True`` for a ``write`` or ``both`` stream.
        """
        return self.mode in ("write", "both")

    def readinto(  # type: ignore[override]  # narrower than RawIOBase's buffer type
        self, buffer: bytearray | memoryview
    ) -> int:
        """Read bytes into a buffer, waiting for the daemon if there are none.

        :param buffer: where to put the bytes.
        :returns: how many bytes; 0 when the daemon has sent everything.
        :raises LibvirtError: if the daemon reports a failure.
        :raises UnsupportedOperation: if the stream is write-only.
        """
        if not self.readable():
            raise io.UnsupportedOperation("this stream is write-only")

        while not self._pending and not self._eof:
            self._take(self._events.get())
        if not self._pending:
            return 0

        view = memoryview(buffer)
        count = min(len(view), len(self._pending))
        view[:count] = self._pending[:count]
        self._pending = self._pending[count:]
        return count

    def write(  # type: ignore[override]  # narrower than RawIOBase's buffer type
        self, data: bytes | bytearray | memoryview
    ) -> int:
        """Send bytes to the daemon.

        :param data: the bytes.
        :returns: how many bytes were sent: all of them.
        :raises UnsupportedOperation: if the stream is read-only.
        """
        if not self.writable():
            raise io.UnsupportedOperation("this stream is read-only")

        view = memoryview(data)
        for start in range(0, len(view), CHUNK_SIZE):
            self._rpc.send_stream_data(
                self.serial, bytes(view[start : start + CHUNK_SIZE])
            )
        return len(view)

    def close(self) -> None:
        """End the stream: finish what we send, or give up on what we read."""
        if self.closed:
            return
        try:
            self._finish()
        finally:
            super().close()

    def _take(self, event: StreamEvent) -> None:
        """Handle one event while reading.

        :param event: what the connection delivered.
        :raises Exception: the error the daemon (or the connection) reported.
        """
        if event.kind == "data":
            self._pending += event.data
            return

        self._eof = True
        if event.kind in ("closed", "error"):
            self._dead = True
        if event.error is not None:
            raise event.error

    def _finish(self) -> None:
        """Tell the daemon we are done, and wait for it to confirm.

        A stream we were still reading is given up (aborted) instead.
        """
        if self._dead:
            return
        self._dead = True

        if self.mode == "read" and not self._eof:
            self._rpc.abort_stream(self.serial)
            return

        self._rpc.finish_stream(self.serial)
        with contextlib.suppress(queue.Empty, Exception):
            while self._events.get(timeout=CLOSE_TIMEOUT_SECONDS).kind not in (
                "closed",
                "error",
            ):
                pass


class AsyncRemoteStream:
    """A stream to or from a daemon, for ``async`` code."""

    def __init__(self, rpc: AsyncRpc, mode: Mode) -> None:
        """Create the stream; the connection sets ``serial`` when the call is sent.

        :param rpc: the connection the stream is on.
        :param mode: ``read``, ``write`` or ``both`` (a console).
        """
        self.mode = mode
        self.serial = -1
        self.reply: Any = None
        """What the call that opened the stream returned."""

        self._rpc = rpc
        self._events: asyncio.Queue[StreamEvent] = asyncio.Queue()
        self._pending = b""

        self._eof = False
        self._dead = False
        self._closed = False

    def deliver(self, event: StreamEvent) -> None:
        """Receive what the connection read for this stream (in the event loop).

        :param event: the data, the end, or the error.
        """
        self._events.put_nowait(event)

    async def read(self, size: int = -1) -> bytes:
        """Read bytes, waiting for the daemon if there are none.

        :param size: the most bytes to return; -1 reads until the end.
        :returns: the bytes; empty when the daemon has sent everything.
        :raises LibvirtError: if the daemon reports a failure.
        """
        self._check_readable()
        while not self._eof and (size < 0 or len(self._pending) < size):
            self._take(await self._events.get())

        count = len(self._pending) if size < 0 else min(size, len(self._pending))
        data, self._pending = self._pending[:count], self._pending[count:]
        return data

    async def read_chunk(self) -> bytes:
        """Read the next piece the daemon sent.

        :returns: the bytes; empty when the daemon has sent everything.
        :raises LibvirtError: if the daemon reports a failure.
        """
        self._check_readable()
        while not self._pending and not self._eof:
            self._take(await self._events.get())
        data, self._pending = self._pending, b""
        return data

    async def write(self, data: bytes) -> int:
        """Send bytes to the daemon.

        :param data: the bytes.
        :returns: how many bytes were sent: all of them.
        :raises UnsupportedOperation: if the stream is read-only.
        """
        if self.mode == "read":
            raise io.UnsupportedOperation("this stream is read-only")

        for start in range(0, len(data), CHUNK_SIZE):
            await self._rpc.send_stream_data(
                self.serial, data[start : start + CHUNK_SIZE]
            )
        return len(data)

    async def close(self) -> None:
        """End the stream: finish what we send, or give up on what we read."""
        if self._closed:
            return
        self._closed = True
        if self._dead:
            return
        self._dead = True

        if self.mode == "read" and not self._eof:
            await self._rpc.abort_stream(self.serial)
            return

        await self._rpc.finish_stream(self.serial)
        with contextlib.suppress(asyncio.TimeoutError, Exception):
            while True:
                event = await asyncio.wait_for(
                    self._events.get(), CLOSE_TIMEOUT_SECONDS
                )
                if event.kind in ("closed", "error"):
                    break

    def __aiter__(self: AsyncSelf) -> AsyncSelf:
        """Iterate over the pieces the daemon sends.

        :returns: the stream.
        """
        return self

    async def __anext__(self) -> bytes:
        """Read the next piece.

        :returns: the bytes.
        :raises StopAsyncIteration: when the daemon has sent everything.
        """
        data = await self.read_chunk()
        if not data:
            raise StopAsyncIteration
        return data

    async def __aenter__(self: AsyncSelf) -> AsyncSelf:
        """Use the stream in an ``async with`` block.

        :returns: the stream.
        """
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the stream when the block ends.

        :param exception_type: the exception class, if the block raised.
        :param exception: the exception, if the block raised.
        :param traceback: its traceback, if the block raised.
        """
        await self.close()

    def _check_readable(self) -> None:
        """Refuse to read a write-only stream.

        :raises UnsupportedOperation: if it is write-only.
        """
        if self.mode == "write":
            raise io.UnsupportedOperation("this stream is write-only")

    def _take(self, event: StreamEvent) -> None:
        """Handle one event while reading.

        :param event: what the connection delivered.
        :raises Exception: the error the daemon (or the connection) reported.
        """
        if event.kind == "data":
            self._pending += event.data
            return

        self._eof = True
        if event.kind in ("closed", "error"):
            self._dead = True
        if event.error is not None:
            raise event.error
