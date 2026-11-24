"""A tiny libvirt RPC server for testing remote transports.

It answers the calls that opening a connection needs, plus the version and the
host name, and records the name the client opened. It speaks the real framing,
so a client that works against it handles real daemons' bytes the same way.
"""

import base64
import hashlib
import hmac
import os
import sys
import threading
from collections.abc import Callable
from typing import Any

from libvirtpy.rpc import xdr
from libvirtpy.rpc.procedure import Procedure
from libvirtpy.rpc.protocol import procedures, types

HEADER = xdr.StructType(types.VirNetMessageHeader)
ERROR = xdr.StructType(types.Error)
LIB_VERSION = 12345
HOSTNAME = "remote-host"


class ScramServer:
    """The server side of SCRAM, to check what the client sends."""

    def __init__(self, password: str, algorithm: str) -> None:
        """Create the server's secrets.

        :param password: the password it expects.
        :param algorithm: ``sha1`` or ``sha256``.
        """
        self.algorithm = algorithm
        self.salt = b"fixed-test-salt"
        self.iterations = 4096
        self.salted = hashlib.pbkdf2_hmac(
            algorithm, password.encode(), self.salt, self.iterations
        )
        self.client_first_bare = ""
        self.server_first = ""
        self.nonce = ""

    def first(self, client_first: str) -> str:
        """Answer the client-first message.

        :param client_first: the client's first message.
        :returns: the server-first message.
        """
        self.client_first_bare = client_first.split(",", 2)[2]
        client_nonce = dict(p.split("=", 1) for p in self.client_first_bare.split(","))[
            "r"
        ]
        self.nonce = client_nonce + "server-part"
        salt = base64.b64encode(self.salt).decode()
        self.server_first = f"r={self.nonce},s={salt},i={self.iterations}"
        return self.server_first

    def final(self, client_final: str) -> str | None:
        """Check the client's proof.

        :param client_final: the client-final message.
        :returns: the server-final message, or ``None`` if the proof is wrong.
        """
        without_proof, _, proof_text = client_final.rpartition(",p=")
        message = (
            f"{self.client_first_bare},{self.server_first},{without_proof}".encode()
        )
        client_key = self._hmac(self.salted, b"Client Key")
        stored_key = hashlib.new(self.algorithm, client_key).digest()
        signature = self._hmac(stored_key, message)

        proof = base64.b64decode(proof_text)
        recovered = bytes(a ^ b for a, b in zip(proof, signature, strict=True))
        if hashlib.new(self.algorithm, recovered).digest() != stored_key:
            return None
        server_key = self._hmac(self.salted, b"Server Key")
        return "v=" + base64.b64encode(self._hmac(server_key, message)).decode()

    def _hmac(self, key: bytes, message: bytes) -> bytes:
        return hmac.new(key, message, self.algorithm).digest()


class FakeRpcServer:
    """Serves one connection."""

    def __init__(self, sasl: tuple[str, str, str] | None = None) -> None:
        """Create a server that has not seen any call yet.

        :param sasl: ``(mechanism, user, password)`` to demand SASL; ``None`` for
            no authentication.
        """
        self.opened: list[str] = []
        self.flags: list[int] = []
        self.sasl = sasl
        self.scram: ScramServer | None = None
        self.registered: dict[int, int] = {}
        """The event subscriptions: callback id -> event id."""
        self.deregistered: list[int] = []
        self.pongs = 0
        self.pings = 0
        """Keepalive pings received from the client."""
        self.answer_pings = True
        self.silent: set[str] = set()
        """Procedures that are never answered (a hung daemon)."""
        self.delayed: dict[str, float] = {}
        """Procedures answered late: name -> seconds."""
        self.uploaded = b""
        self.aborted: list[int] = []
        self.streams: dict[int, str] = {}
        """The open streams: serial -> ``upload`` or ``echo``."""
        self._next_callback = 1
        self._send: Callable[[bytes], None] | None = None
        self._send_lock = threading.Lock()

    def serve(
        self, receive: Callable[[], bytes], send: Callable[[bytes], None]
    ) -> None:
        """Answer calls until the client closes the connection.

        :param receive: waits for bytes; returns nothing at the end.
        :param send: sends bytes to the client.
        """
        self._send = send
        buffer = bytearray()
        while True:
            chunk = receive()
            if not chunk:
                return
            buffer += chunk
            for packet in self._cut(buffer):
                answer = self._answer(packet)
                if answer:
                    self.write(answer)

    def write(self, data: bytes) -> None:
        """Send bytes to the client, one writer at a time.

        :param data: the bytes.
        """
        assert self._send is not None
        with self._send_lock:
            self._send(data)

    def push_lifecycle(
        self, callback_id: int, name: str, event: int, detail: int = 0
    ) -> None:
        """Push a domain lifecycle event, as a daemon does when something happens.

        :param callback_id: the subscription it answers.
        :param name: the domain name.
        :param event: ``virDomainEventType``.
        :param detail: the detail code.
        """
        domain = types.NonnullDomain(name=name, uuid=bytes(16), id=1)
        message = types.DomainEventCallbackLifecycleMsg(
            callback_id=callback_id,
            msg=types.DomainEventLifecycleMsg(dom=domain, event=event, detail=detail),
        )
        procedure = procedures.DOMAIN_EVENT_CALLBACK_LIFECYCLE
        self.write(self._message(procedure.number, message))

    def ping(self) -> None:
        """Send a keepalive ping, which the client must answer with a pong."""
        header = types.VirNetMessageHeader(
            prog=types.KEEPALIVE_PROGRAM,
            vers=types.KEEPALIVE_PROTOCOL_VERSION,
            proc=int(types.KeepaliveProcedure.PING),
            type=types.VirNetMessageType.MESSAGE,
            serial=1,
            status=types.VirNetMessageStatus.OK,
        )
        body = xdr.encode(HEADER, header)
        self.write((4 + len(body)).to_bytes(4, "big") + body)

    def _stream_call(
        self, header: types.VirNetMessageHeader, procedure: Any, payload: bytes
    ) -> bytes | None:
        """Answer the calls that find objects or open streams.

        :param header: the call's header.
        :param procedure: its procedure.
        :param payload: its arguments.
        :returns: the framed reply (and stream packets), or ``None`` if it is not
            one of these calls.
        """
        name = procedure.name
        if name == "domain_lookup_by_name":
            domain = types.NonnullDomain(name="vm", uuid=bytes(16), id=1)
            return self._reply(header, types.DomainLookupByNameRet(dom=domain))
        if name == "storage_pool_lookup_by_name":
            pool = types.NonnullStoragePool(name="pool", uuid=bytes(16))
            return self._reply(header, types.StoragePoolLookupByNameRet(pool=pool))
        if name == "storage_vol_lookup_by_name":
            args = xdr.decode(xdr.StructType(types.StorageVolLookupByNameArgs), payload)
            volume = types.NonnullStorageVol(pool="pool", name=args.name, key=args.name)
            return self._reply(header, types.StorageVolLookupByNameRet(vol=volume))
        if name in ("storage_vol_download", "domain_screenshot"):
            return self._send_file(header, procedure, payload)
        if name == "storage_vol_upload":
            self.streams[header.serial] = "upload"
            return self._reply(header, None)
        if name in ("domain_open_console", "domain_open_channel"):
            self.streams[header.serial] = "echo"
            return self._reply(header, None)
        return None

    def _send_file(
        self, header: types.VirNetMessageHeader, procedure: Any, payload: bytes
    ) -> bytes:
        """Answer a call that downloads: the reply, then the data, then the end.

        A volume named ``broken`` fails half way, and one named ``slow`` never
        finishes, to test errors and aborts.

        :param header: the call's header.
        :param procedure: its procedure.
        :param payload: its arguments.
        :returns: the framed reply and stream packets.
        """
        if procedure is procedures.DOMAIN_SCREENSHOT:
            reply = self._reply(header, types.DomainScreenshotRet(mime="image/png"))
        else:
            reply = self._reply(header, None)

        number = header.proc
        parts = [reply, self._stream(header.serial, number, 2, b"hello ")]
        if b"broken" in payload:
            error = types.Error(
                code=38,
                domain=0,
                message="disk fell over",
                level=2,
                dom=None,
                str1=None,
                str2=None,
                str3=None,
                int1=0,
                int2=0,
                net=None,
            )
            parts.append(
                self._stream(header.serial, number, 1, xdr.encode(ERROR, error))
            )
            return b"".join(parts)

        if b"slow" in payload:
            return b"".join(parts)

        parts.append(self._stream(header.serial, number, 2, b"world"))
        parts.append(self._stream(header.serial, number, 2, b""))  # end of data
        return b"".join(parts)

    def _from_client_stream(
        self, header: types.VirNetMessageHeader, payload: bytes
    ) -> bytes:
        """Handle a stream packet that the client sent.

        :param header: the packet's header.
        :param payload: its data.
        :returns: what to send back; nothing for data of an upload.
        """
        kind = self.streams.get(header.serial)
        status = header.status
        if status == types.VirNetMessageStatus.ERROR:
            self.aborted.append(header.serial)
            self.streams.pop(header.serial, None)
            return b""
        if status == types.VirNetMessageStatus.OK:
            self.streams.pop(header.serial, None)
            return self._stream(header.serial, header.proc, 0, b"")
        if kind == "upload":
            self.uploaded += payload
            return b""
        return self._stream(header.serial, header.proc, 2, payload.upper())

    @staticmethod
    def _stream(serial: int, number: int, status: int, payload: bytes) -> bytes:
        """Frame a packet of a stream.

        :param serial: the stream.
        :param number: the procedure that opened it.
        :param status: 0 ok, 1 error, 2 continue.
        :param payload: the data.
        :returns: the framed packet.
        """
        header = types.VirNetMessageHeader(
            prog=types.REMOTE_PROGRAM,
            vers=types.REMOTE_PROTOCOL_VERSION,
            proc=number,
            type=types.VirNetMessageType.STREAM,
            serial=serial,
            status=types.VirNetMessageStatus(status),
        )
        body = xdr.encode(HEADER, header) + payload
        return (4 + len(body)).to_bytes(4, "big") + body

    def _message(self, procedure_number: int, message: Any) -> bytes:
        """Frame an unsolicited message.

        :param procedure_number: the event procedure.
        :param message: its struct.
        :returns: the framed packet.
        """
        header = types.VirNetMessageHeader(
            prog=types.REMOTE_PROGRAM,
            vers=types.REMOTE_PROTOCOL_VERSION,
            proc=procedure_number,
            type=types.VirNetMessageType.MESSAGE,
            serial=0,
            status=types.VirNetMessageStatus.OK,
        )
        body = xdr.encode(HEADER, header)
        body += xdr.encode(xdr.StructType(type(message)), message)
        return (4 + len(body)).to_bytes(4, "big") + body

    def _cut(self, buffer: bytearray) -> list[bytes]:
        """Take the complete packets out of the buffer.

        :param buffer: received bytes; consumed packets are removed.
        :returns: the packets without their length prefix.
        """
        packets = []
        while len(buffer) >= 4:
            length = int.from_bytes(buffer[:4], "big")
            if len(buffer) < length:
                break
            packets.append(bytes(buffer[4:length]))
            del buffer[:length]
        return packets

    def _answer(self, packet: bytes) -> bytes:
        """Build the reply to one call.

        :param packet: header and arguments.
        :returns: the framed reply.
        """
        decoder = xdr.Decoder(packet)
        header = HEADER.decode(decoder)
        payload = decoder.read(decoder.remaining)
        if header.prog == types.KEEPALIVE_PROGRAM:
            self.pongs += header.proc == types.KeepaliveProcedure.PONG
            if header.proc == types.KeepaliveProcedure.PING:
                self.pings += 1
                return self._pong() if self.answer_pings else b""
            return b""
        if header.type == types.VirNetMessageType.STREAM:
            return self._from_client_stream(header, payload)
        procedure = procedures.PROCEDURES[header.proc]
        if procedure.name in self.silent:
            return b""
        if procedure.name in self.delayed:
            late = self._without_delay(header, procedure, payload)
            threading.Timer(self.delayed[procedure.name], self.write, [late]).start()
            return b""
        stream_reply = self._stream_call(header, procedure, payload)
        if stream_reply is not None:
            return stream_reply

        if procedure is procedures.CONNECT_DOMAIN_EVENT_CALLBACK_REGISTER_ANY:
            args = xdr.decode(
                xdr.StructType(types.ConnectDomainEventCallbackRegisterAnyArgs),
                payload,
            )
            callback_id = self._next_callback
            self._next_callback += 1
            self.registered[callback_id] = args.event_id
            reply = types.ConnectDomainEventCallbackRegisterAnyRet(
                callback_id=callback_id
            )
            return self._reply(header, reply)
        if procedure is procedures.CONNECT_DOMAIN_EVENT_CALLBACK_DEREGISTER_ANY:
            args = xdr.decode(
                xdr.StructType(types.ConnectDomainEventCallbackDeregisterAnyArgs),
                payload,
            )
            self.deregistered.append(args.callback_id)
            return self._reply(header, None)
        if procedure is procedures.AUTH_LIST:
            kind = types.AuthType.NONE if self.sasl is None else types.AuthType.SASL
            return self._reply(header, types.AuthListRet(types=[kind]))
        if procedure.name.startswith("auth_sasl"):
            return self._sasl(header, procedure.name, payload)
        if procedure is procedures.CONNECT_OPEN:
            arguments = xdr.decode(xdr.StructType(types.ConnectOpenArgs), payload)
            self.opened.append(str(arguments.name))
            self.flags.append(arguments.flags)
            return self._reply(header, None)
        if procedure is procedures.CONNECT_GET_LIB_VERSION:
            return self._reply(
                header, types.ConnectGetLibVersionRet(lib_ver=LIB_VERSION)
            )
        if procedure is procedures.CONNECT_GET_HOSTNAME:
            return self._reply(header, types.ConnectGetHostnameRet(hostname=HOSTNAME))
        return self._error(header)

    def _pong(self) -> bytes:
        """Build the answer to a keepalive ping.

        :returns: the framed pong.
        """
        header = types.VirNetMessageHeader(
            prog=types.KEEPALIVE_PROGRAM,
            vers=types.KEEPALIVE_PROTOCOL_VERSION,
            proc=int(types.KeepaliveProcedure.PONG),
            type=types.VirNetMessageType.MESSAGE,
            serial=0,
            status=types.VirNetMessageStatus.OK,
        )
        body = xdr.encode(HEADER, header)
        return (4 + len(body)).to_bytes(4, "big") + body

    def _without_delay(
        self,
        header: types.VirNetMessageHeader,
        procedure: Procedure[Any, Any],
        payload: bytes,
    ) -> bytes:
        """Build the reply of a delayed procedure as if it was not delayed.

        :param header: the call's header.
        :param procedure: the procedure.
        :param payload: its arguments.
        :returns: the framed reply.
        """
        delayed, self.delayed = self.delayed, {}
        try:
            return self._answer(self._framed_call(header, payload))
        finally:
            self.delayed = delayed

    def _framed_call(self, header: types.VirNetMessageHeader, payload: bytes) -> bytes:
        """Rebuild the bytes of a call (header and arguments).

        :param header: the call's header.
        :param payload: its arguments.
        :returns: the packet without its length prefix.
        """
        return xdr.encode(HEADER, header) + payload

    def _sasl(
        self, header: types.VirNetMessageHeader, name: str, payload: bytes
    ) -> bytes:
        """Answer a SASL call (PLAIN or SCRAM only).

        :param header: the call's header.
        :param name: the procedure name.
        :param payload: its arguments.
        :returns: the framed reply.
        """
        assert self.sasl is not None
        mechanism, user, password = self.sasl
        if name == "auth_sasl_init":
            return self._reply(
                header, types.AuthSaslInitRet(mechlist=f"GSSAPI,{mechanism}")
            )

        if name == "auth_sasl_start":
            args = xdr.decode(xdr.StructType(types.AuthSaslStartArgs), payload)
            data = bytes(c & 255 for c in args.data)
            if args.mech != mechanism:
                return self._auth_error(header)
            if mechanism == "PLAIN":
                return self._sasl_done(
                    header, data == f"\0{user}\0{password}".encode(), b""
                )
            algorithm = "sha256" if mechanism.endswith("256") else "sha1"
            self.scram = ScramServer(password, algorithm)
            first = self.scram.first(data.decode())
            return self._sasl_reply(header, False, first.encode())

        args2 = xdr.decode(xdr.StructType(types.AuthSaslStepArgs), payload)
        assert self.scram is not None
        final = self.scram.final(bytes(c & 255 for c in args2.data).decode())
        if final is None:
            return self._auth_error(header)
        return self._sasl_reply(header, True, final.encode())

    def _sasl_done(
        self, header: types.VirNetMessageHeader, ok: bool, data: bytes
    ) -> bytes:
        """Finish the conversation, successfully or not.

        :param header: the call's header.
        :param ok: whether the credentials were right.
        :param data: final data for the client.
        :returns: the framed reply.
        """
        return self._sasl_reply(header, True, data) if ok else self._auth_error(header)

    def _sasl_reply(
        self, header: types.VirNetMessageHeader, complete: bool, data: bytes
    ) -> bytes:
        """Frame a start or step reply.

        :param header: the call's header.
        :param complete: whether authentication is finished.
        :param data: the server's data.
        :returns: the framed reply.
        """
        chars = [b - 256 if b > 127 else b for b in data]
        cls = (
            types.AuthSaslStartRet
            if header.proc == procedures.AUTH_SASL_START.number
            else types.AuthSaslStepRet
        )
        return self._reply(
            header, cls(complete=int(complete), nil=int(not data), data=chars)
        )

    def _auth_error(self, header: types.VirNetMessageHeader) -> bytes:
        """Frame an authentication failure.

        :param header: the call's header.
        :returns: the framed reply.
        """
        error = types.Error(
            code=45,
            domain=0,
            message="authentication failed",
            level=2,
            dom=None,
            str1=None,
            str2=None,
            str3=None,
            int1=0,
            int2=0,
            net=None,
        )
        return _frame(header, types.VirNetMessageStatus.ERROR, xdr.encode(ERROR, error))

    def _reply(self, call: types.VirNetMessageHeader, result: Any) -> bytes:
        """Frame a successful reply.

        :param call: the header of the call.
        :param result: the return struct, or ``None``.
        :returns: the framed reply.
        """
        payload = b""
        if result is not None:
            payload = xdr.encode(xdr.StructType(type(result)), result)
        return _frame(call, types.VirNetMessageStatus.OK, payload)

    def _error(self, call: types.VirNetMessageHeader) -> bytes:
        """Frame an "unsupported" error.

        :param call: the header of the call.
        :returns: the framed reply.
        """
        error = types.Error(
            code=3,
            domain=0,
            message="not supported by the fake",
            level=2,
            dom=None,
            str1=None,
            str2=None,
            str3=None,
            int1=0,
            int2=0,
            net=None,
        )
        return _frame(call, types.VirNetMessageStatus.ERROR, xdr.encode(ERROR, error))


def _frame(
    call: types.VirNetMessageHeader, status: types.VirNetMessageStatus, payload: bytes
) -> bytes:
    """Frame a reply to ``call``.

    :param call: the header of the call.
    :param status: ok or error.
    :param payload: the encoded body.
    :returns: length prefix, header and body.
    """
    header = types.VirNetMessageHeader(
        prog=call.prog,
        vers=call.vers,
        proc=call.proc,
        type=types.VirNetMessageType.REPLY,
        serial=call.serial,
        status=status,
    )
    body = xdr.encode(HEADER, header) + payload
    return (4 + len(body)).to_bytes(4, "big") + body


def main() -> None:
    """Serve the connection on standard input and output (for the fake ``ssh``)."""
    server = FakeRpcServer()
    stdout = sys.stdout.buffer

    def send(data: bytes) -> None:
        """Write to standard output.

        :param data: the bytes.
        """
        stdout.write(data)
        stdout.flush()

    server.serve(lambda: os.read(0, 65536), send)


if __name__ == "__main__":
    main()
