"""The libvirt RPC session without any I/O.

``Session`` turns calls into bytes to send and received bytes into results. A
packet is a 4-byte length (counting itself), a 24-byte header and an XDR
payload. The sync and the async client only move the bytes.
"""

from dataclasses import dataclass
from typing import Any

from libvirtpy.errors import LibvirtPyError
from libvirtpy.rpc import xdr
from libvirtpy.rpc.errors import LibvirtError, error_class_for
from libvirtpy.rpc.procedure import Procedure
from libvirtpy.rpc.protocol import types
from libvirtpy.rpc.protocol.procedures import PROCEDURES

__all__ = [
    "CallTimeoutError",
    "Completed",
    "ConnectionLostError",
    "ProtocolError",
    "ServerEvent",
    "Session",
    "StreamEvent",
]

LENGTH_SIZE = 4
HEADER_TYPE = xdr.StructType(types.VirNetMessageHeader)
ERROR_TYPE = xdr.StructType(types.Error)


class ProtocolError(LibvirtPyError):
    """The daemon sent something that is not valid libvirt RPC."""


class ConnectionLostError(ProtocolError, ConnectionError):
    """The connection to the daemon ended (it closed it, or ``ssh`` exited)."""


class CallTimeoutError(ProtocolError, TimeoutError):
    """A call got no reply in time; the connection itself is still usable.

    The reply may still arrive later: the session drops it.
    """


@dataclass(frozen=True)
class Completed:
    """The outcome of a call."""

    serial: int
    result: Any = None
    error: LibvirtError | None = None


@dataclass(frozen=True)
class StreamEvent:
    """Something that happened on an open data stream."""

    serial: int
    """The stream, which has the serial of the call that opened it."""
    kind: str
    """``data`` (bytes arrived), ``end`` (the daemon finished sending),
    ``closed`` (the daemon confirmed that we finished) or ``error``. ``end`` does
    not close the stream: finish it to complete the handshake."""
    data: bytes = b""
    error: Exception | None = None


@dataclass(frozen=True)
class ServerEvent:
    """A message the daemon pushed on its own: something happened."""

    procedure: Procedure[Any, Any]
    """The event's procedure; its ``message`` is the struct below."""
    message: Any
    """The decoded message struct."""


class Session:
    """The state of one RPC connection: serials, pending calls, partial input."""

    def __init__(self) -> None:
        """Create a session with no calls in flight."""
        self._next_serial = 1
        self._pending: dict[int, Procedure[Any, Any]] = {}
        self._abandoned: set[int] = set()

        self._buffer = bytearray()
        self._outgoing = bytearray()
        self._events: list[ServerEvent] = []

        self._streams: dict[int, int] = {}
        self._finishing: set[int] = set()
        self._stream_events: list[StreamEvent] = []

    def call(
        self,
        procedure: Procedure[Any, Any],
        args: Any = None,
        *,
        stream: bool = False,
    ) -> tuple[int, bytes]:
        """Build the packet of a call.

        :param procedure: the procedure to call.
        :param args: the arguments struct, or ``None`` if the procedure has none.
        :param stream: the call opens a data stream, which gets the call's serial.
        :returns: the serial of the call and the bytes to send.
        :raises ProtocolError: if the arguments do not match the procedure.
        """
        if (procedure.args is None) != (args is None):
            raise ProtocolError(f"wrong arguments for {procedure.name}")

        serial = self._next_serial
        self._next_serial += 1
        self._pending[serial] = procedure
        if stream:
            self._streams[serial] = procedure.number
        payload = b"" if args is None else xdr.encode(_arguments_type(procedure), args)

        header = types.VirNetMessageHeader(
            prog=types.REMOTE_PROGRAM,
            vers=types.REMOTE_PROTOCOL_VERSION,
            proc=procedure.number,
            type=types.VirNetMessageType.CALL,
            serial=serial,
            status=types.VirNetMessageStatus.OK,
        )
        return serial, _packet(header, payload)

    def feed(self, data: bytes) -> list[Completed]:
        """Add received bytes and collect the calls they finish.

        Packets that are not replies are handled here: a keepalive ping queues
        a pong (see ``take_outgoing``); events and streams are dropped.

        :param data: bytes from the socket.
        :returns: the calls that completed, in arrival order.
        :raises ProtocolError: if a packet is malformed.
        """
        self._buffer += data
        completed = []

        for packet in self._packets():
            reply = self._handle(packet)
            if reply is not None:
                completed.append(reply)
        return completed

    def abandon(self, serial: int) -> None:
        """Stop waiting for the reply of a call, and drop it if it comes later.

        :param serial: the call, as returned by ``call``.
        """
        if self._pending.pop(serial, None) is not None:
            self._abandoned.add(serial)

    def keepalive_ping(self) -> bytes:
        """Build a keepalive ping; a live daemon answers with a pong.

        :returns: the bytes to send.
        """
        ping = types.VirNetMessageHeader(
            prog=types.KEEPALIVE_PROGRAM,
            vers=types.KEEPALIVE_PROTOCOL_VERSION,
            proc=int(types.KeepaliveProcedure.PING),
            type=types.VirNetMessageType.MESSAGE,
            serial=0,
            status=types.VirNetMessageStatus.OK,
        )
        return _packet(ping, b"")

    def take_outgoing(self) -> bytes:
        """Take the bytes the session wants sent without being asked (pongs).

        :returns: the bytes, possibly empty.
        """
        data = bytes(self._outgoing)
        self._outgoing.clear()
        return data

    def take_events(self) -> list[ServerEvent]:
        """Take the events that arrived since the last call.

        :returns: the events, oldest first, possibly none.
        """
        events = self._events
        self._events = []
        return events

    def take_stream_events(self) -> list[StreamEvent]:
        """Take what happened on the open streams since the last call.

        :returns: the events, oldest first, possibly none.
        """
        events = self._stream_events
        self._stream_events = []
        return events

    def stream_data(self, serial: int, data: bytes) -> bytes:
        """Build the packet that sends data on a stream.

        :param serial: the stream.
        :param data: the bytes.
        :returns: the bytes to send; nothing if the stream is already over.
        """
        return self._stream_packet(serial, types.VirNetMessageStatus.CONTINUE, data)

    def stream_finish(self, serial: int) -> bytes:
        """Build the packet that says we have sent everything.

        The daemon answers with a ``closed`` stream event.

        :param serial: the stream.
        :returns: the bytes to send; nothing if the stream is already over.
        """
        if serial in self._streams:
            self._finishing.add(serial)
        return self._stream_packet(serial, types.VirNetMessageStatus.OK, b"")

    def stream_abort(self, serial: int) -> bytes:
        """Build the packet that gives up on a stream, and forget the stream.

        :param serial: the stream.
        :returns: the bytes to send; nothing if the stream is already over.
        """
        packet = self._stream_packet(serial, types.VirNetMessageStatus.ERROR, b"")
        self._streams.pop(serial, None)
        return packet

    def _stream_packet(
        self, serial: int, status: types.VirNetMessageStatus, payload: bytes
    ) -> bytes:
        """Frame a packet of an open stream.

        :param serial: the stream.
        :param status: continue, ok or error.
        :param payload: the data.
        :returns: the bytes, or nothing if the stream is not open.
        """
        number = self._streams.get(serial)
        if number is None:
            return b""

        header = types.VirNetMessageHeader(
            prog=types.REMOTE_PROGRAM,
            vers=types.REMOTE_PROTOCOL_VERSION,
            proc=number,
            type=types.VirNetMessageType.STREAM,
            serial=serial,
            status=status,
        )
        return _packet(header, payload)

    def _record_stream(self, header: types.VirNetMessageHeader, payload: bytes) -> None:
        """Turn a packet of an open stream into a stream event.

        :param header: the packet's header.
        :param payload: its body.
        """
        serial = header.serial
        if serial not in self._streams:
            return

        if header.status == types.VirNetMessageStatus.CONTINUE:
            # An empty packet is libvirt's end-of-data marker; the stream stays
            # open until we finish it and the daemon confirms.
            kind = "data" if payload else "end"
            self._stream_events.append(StreamEvent(serial, kind, payload))
            return

        del self._streams[serial]
        if header.status == types.VirNetMessageStatus.ERROR:
            error = _to_exception(xdr.decode(ERROR_TYPE, payload))
            self._stream_events.append(StreamEvent(serial, "error", error=error))
            return

        self._finishing.discard(serial)
        self._stream_events.append(StreamEvent(serial, "closed"))

    def _packets(self) -> list[bytes]:
        """Cut complete packets off the buffer.

        :returns: the packets, without their length prefix.
        :raises ProtocolError: if a length is impossible.
        """
        packets = []
        while len(self._buffer) >= LENGTH_SIZE:
            length = int.from_bytes(self._buffer[:LENGTH_SIZE], "big")
            if length < LENGTH_SIZE + types.VIR_NET_MESSAGE_HEADER_MAX:
                raise ProtocolError(f"packet length {length} is too small")
            if length > types.VIR_NET_MESSAGE_MAX + LENGTH_SIZE:
                raise ProtocolError(f"packet length {length} is too big")
            if len(self._buffer) < length:
                break

            packets.append(bytes(self._buffer[LENGTH_SIZE:length]))
            del self._buffer[:length]
        return packets

    def _handle(self, packet: bytes) -> Completed | None:
        """Process one packet.

        :param packet: header and payload.
        :returns: the finished call, or ``None`` if the packet was not a reply.
        """
        decoder = xdr.Decoder(packet)
        header = HEADER_TYPE.decode(decoder)
        payload = decoder.read(decoder.remaining)

        if header.prog == types.KEEPALIVE_PROGRAM:
            self._answer_keepalive(header)
            return None
        if header.prog != types.REMOTE_PROGRAM:
            return None

        if header.type == types.VirNetMessageType.MESSAGE:
            self._record_event(header, payload)
            return None
        if header.type == types.VirNetMessageType.STREAM:
            self._record_stream(header, payload)
            return None
        if header.type != types.VirNetMessageType.REPLY:
            return None
        return self._complete(header, payload)

    def _complete(
        self, header: types.VirNetMessageHeader, payload: bytes
    ) -> Completed | None:
        """Match a reply to its call and decode it.

        :param header: the reply's header.
        :param payload: the reply's body.
        :returns: the outcome, or ``None`` for the late reply of an abandoned call.
        :raises ProtocolError: if no call is waiting for this serial.
        """
        if header.serial in self._abandoned:
            self._abandoned.discard(header.serial)
            return None

        procedure = self._pending.pop(header.serial, None)
        if procedure is None:
            raise ProtocolError(f"reply to unknown serial {header.serial}")

        if header.status == types.VirNetMessageStatus.ERROR:
            return Completed(
                header.serial, error=_to_exception(xdr.decode(ERROR_TYPE, payload))
            )
        if procedure.ret is None:
            return Completed(header.serial)
        return Completed(header.serial, xdr.decode(_return_type(procedure), payload))

    def _record_event(self, header: types.VirNetMessageHeader, payload: bytes) -> None:
        """Decode a pushed event and queue it; unknown events are dropped.

        :param header: the event's header.
        :param payload: its body.
        """
        procedure = PROCEDURES.get(header.proc)
        if procedure is None or procedure.message is None:
            return
        message = xdr.decode(xdr.StructType(procedure.message), payload)
        self._events.append(ServerEvent(procedure, message))

    def _answer_keepalive(self, header: types.VirNetMessageHeader) -> None:
        """Queue a pong for a keepalive ping.

        :param header: the keepalive packet's header.
        """
        if header.proc != types.KeepaliveProcedure.PING:
            return

        pong = types.VirNetMessageHeader(
            prog=types.KEEPALIVE_PROGRAM,
            vers=types.KEEPALIVE_PROTOCOL_VERSION,
            proc=int(types.KeepaliveProcedure.PONG),
            type=types.VirNetMessageType.MESSAGE,
            serial=header.serial,
            status=types.VirNetMessageStatus.OK,
        )
        self._outgoing += _packet(pong, b"")


def _packet(header: types.VirNetMessageHeader, payload: bytes) -> bytes:
    """Frame a header and a payload.

    :param header: the message header.
    :param payload: the encoded body.
    :returns: the length prefix, the header and the payload.
    """
    body = xdr.encode(HEADER_TYPE, header) + payload
    return (LENGTH_SIZE + len(body)).to_bytes(LENGTH_SIZE, "big") + body


def _arguments_type(procedure: Procedure[Any, Any]) -> xdr.StructType:
    """Describe a procedure's arguments for the codec.

    :param procedure: a procedure that has arguments.
    :returns: the codec type.
    """
    assert procedure.args is not None
    return xdr.StructType(procedure.args)


def _return_type(procedure: Procedure[Any, Any]) -> xdr.StructType:
    """Describe a procedure's return value for the codec.

    :param procedure: a procedure that returns something.
    :returns: the codec type.
    """
    assert procedure.ret is not None
    return xdr.StructType(procedure.ret)


def _to_exception(error: types.Error) -> LibvirtError:
    """Turn the daemon's error struct into an exception.

    :param error: the decoded ``remote_error``.
    :returns: the exception of the class that fits the error code.
    """
    message = error.message or f"libvirt error {error.code}"
    return error_class_for(error.code)(message, code=error.code, domain=error.domain)
