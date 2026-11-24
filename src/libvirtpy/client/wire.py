"""A ``Transport`` that carries operations to real libvirt daemons.

``WireTransport`` turns a ``Request`` (procedure name and arguments by name)
into the generated argument struct, picks the daemon channel of the procedure,
and turns the reply struct back into what the operations expect: ``Handle``s,
text, numbers.
"""

import threading
import time
import uuid
from collections.abc import Iterable
from enum import IntEnum
from typing import Any

from libvirtpy.client.subscribing import (
    SubscriptionPlan,
    event_lookup,
    plan_subscription,
)
from libvirtpy.client.transport import Handle, Request
from libvirtpy.client.types import DomainInfo, DomainState
from libvirtpy.rpc import typed_params, xdr
from libvirtpy.rpc.errors import ErrorNumber, NotSupportedError
from libvirtpy.rpc.options import ConnectionOptions
from libvirtpy.rpc.procedure import Driver, Procedure
from libvirtpy.rpc.protocol import procedures, types
from libvirtpy.rpc.protocol.procedures import PROCEDURES
from libvirtpy.rpc.sasl import SaslCredentials
from libvirtpy.rpc.session import ConnectionLostError, ProtocolError
from libvirtpy.rpc.sockets import REMOTE_KEY, open_channel
from libvirtpy.rpc.stream import Mode, RemoteStream
from libvirtpy.rpc.subscription import DEFAULT_MAX_EVENTS, Subscription
from libvirtpy.rpc.sync import SyncRpc
from libvirtpy.rpc.uri import ConnectionTarget, parse_uri

__all__ = ["WireTransport", "convert_arguments", "convert_reply"]

PROCEDURES_BY_NAME = {procedure.name: procedure for procedure in PROCEDURES.values()}


class WireTransport:
    """Serves requests from real daemons, one socket per daemon, opened lazily."""

    def __init__(
        self,
        target: ConnectionTarget,
        *,
        read_only: bool = False,
        sasl: SaslCredentials | None = None,
        options: ConnectionOptions | None = None,
    ) -> None:
        """Create the transport; nothing is connected until the first request.

        :param target: what the URI asks for.
        :param read_only: use the read-only sockets.
        :param sasl: the user name and password, if the daemon asks for SASL.
        :param options: the call timeout, keepalive and reconnect settings.
        """
        self._target = target
        self._read_only = read_only
        self._sasl = sasl
        self._options = options

        self._channels: dict[str, SyncRpc] = {}
        self._opening = threading.Lock()
        self._closed = False

    @classmethod
    def from_uri(
        cls,
        uri: str,
        *,
        read_only: bool = False,
        sasl: SaslCredentials | None = None,
        options: ConnectionOptions | None = None,
    ) -> WireTransport:
        """Create a transport for a libvirt URI, and check that it connects.

        :param uri: e.g. ``qemu:///system``.
        :param read_only: use the read-only sockets.
        :param sasl: the user name and password, if the daemon asks for SASL.
        :param options: the call timeout, keepalive and reconnect settings.
        :returns: the transport, with the hypervisor channel already open.
        :raises ConnectionError: if the daemon cannot be reached.
        """
        transport = cls(parse_uri(uri), read_only=read_only, sasl=sasl, options=options)
        transport._channel("hypervisor")
        return transport

    def call(self, request: Request) -> object:
        """Send a request to the daemon that serves it.

        :param request: the call to make.
        :returns: the reply, converted for the operations.
        :raises NotSupportedError: if the procedure does not exist.
        :raises LibvirtError: if the daemon reports an error.
        """
        procedure = PROCEDURES_BY_NAME.get(request.procedure)
        if procedure is None:
            raise NotSupportedError(
                f"{request.procedure} is not a libvirt procedure",
                code=ErrorNumber.NO_SUPPORT,
            )

        args = convert_arguments(procedure, request.arguments)
        rpc = self._channel(procedure.driver)
        if request.stream is not None:
            return self._open_stream(rpc, procedure, args, request.stream)
        return convert_reply(procedure, rpc.call(procedure, args))

    def _open_stream(
        self, rpc: SyncRpc, procedure: Procedure[Any, Any], args: Any, mode: Mode
    ) -> RemoteStream:
        """Call a procedure that opens a data stream.

        :param rpc: the connection to the daemon that serves it.
        :param procedure: the procedure.
        :param args: its arguments struct.
        :param mode: which way the data flows.
        :returns: the open stream; ``reply`` has what the call returned.
        """
        stream = RemoteStream(rpc, mode)
        reply = rpc.call(procedure, args, stream=stream)
        stream.reply = convert_reply(procedure, reply)
        return stream

    def subscribe(
        self,
        source: str,
        kinds: Iterable[IntEnum] | None,
        target: object,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> Subscription:
        """Start receiving events.

        :param source: ``domain``, ``network``, ``pool``, ``node_device`` or ``secret``.
        :param kinds: which events; ``None`` for the ``lifecycle`` ones.
        :param target: limit to one object (a reference); ``None`` for all.
        :param max_events: the most events kept for a slow reader.
        :returns: the subscription.
        :raises ValueError: if the source or a kind is unknown.
        """
        plan = plan_subscription(source, kinds)
        handle = None if target is None else self.call(event_lookup(source, target))
        rpc = self._channel(plan.register.driver)

        subscription = Subscription(rpc, plan.deregister, max_events)
        try:
            self._register(subscription, plan, handle, rpc)
        except Exception:
            subscription.close()
            raise
        return subscription

    def close(self) -> None:
        """Close every open channel; the transport does not reconnect after this."""
        self._closed = True
        for channel in set(self._channels.values()):
            channel.close()
        self._channels.clear()

    def _channel(self, driver: Driver) -> SyncRpc:
        """Return the channel of a driver, connecting on first use.

        A channel whose connection was lost is replaced by a new one if the
        connection options ask for reconnecting; otherwise it is returned and the
        call on it fails with ``ConnectionLostError``.

        :param driver: the part of libvirt that serves the call.
        :returns: the channel; a monolithic ``libvirtd`` shares one for all.
        :raises ConnectionLostError: if the transport was closed.
        :raises ConnectionError: if the connection cannot be opened again.
        """
        key = REMOTE_KEY if self._target.remote else driver
        with self._opening:
            if self._closed:
                raise ConnectionLostError("the client is closed")

            channel = self._channels.get(key)
            if channel is None:
                return self._open(driver, key)
            if channel.failure is None or not self._reconnecting():
                return channel

            self._forget(channel)
            return self._reopen(driver, key)

    def _reconnecting(self) -> bool:
        """Tell whether lost connections are opened again.

        :returns: ``True`` if the options ask for it.
        """
        return self._options is not None and self._options.reconnects

    def _reopen(self, driver: Driver, key: str) -> SyncRpc:
        """Open a channel again after its connection was lost.

        :param driver: the part of libvirt that serves the call.
        :param key: the channel's key.
        :returns: the new channel.
        :raises ConnectionError: if every attempt failed.
        """
        assert self._options is not None
        waits = self._options.reconnect_waits()
        failure: Exception | None = None

        for wait in waits:
            time.sleep(wait)
            try:
                return self._open(driver, key)
            except (ConnectionError, OSError) as error:
                failure = error
        raise ConnectionError(
            f"cannot reconnect after {len(waits)} attempts: {failure}"
        ) from failure

    def _forget(self, channel: SyncRpc) -> None:
        """Drop a dead channel and close what is left of it.

        :param channel: the channel.
        """
        for key in [key for key, value in self._channels.items() if value is channel]:
            del self._channels[key]
        channel.close()

    def _register(
        self,
        subscription: Subscription,
        plan: SubscriptionPlan,
        handle: object,
        rpc: SyncRpc,
    ) -> None:
        """Register the events of a subscription on a connection.

        :param subscription: the subscription.
        :param plan: which registrations to make.
        :param handle: the object to limit to, or ``None``.
        :param rpc: the connection.
        """
        if self._reconnecting():
            rpc.when_lost(
                lambda _error: threading.Thread(
                    target=self._restore,
                    args=(subscription, plan, handle),
                    daemon=True,
                ).start()
            )
        else:
            rpc.when_lost(subscription.lost)

        for arguments in plan.arguments(handle):
            rpc.call(
                plan.register,
                convert_arguments(plan.register, arguments),
                on_result=lambda reply: subscription.attach(reply.callback_id),
            )

    def _restore(
        self, subscription: Subscription, plan: SubscriptionPlan, handle: object
    ) -> None:
        """Register a subscription again on a new connection (own thread).

        :param subscription: the subscription of the lost connection.
        :param plan: which registrations to make.
        :param handle: the object to limit to, or ``None``.
        """
        try:
            rpc = self._channel(plan.register.driver)
            if subscription.rebind(rpc):
                self._register(subscription, plan, handle, rpc)
        except Exception as failure:  # background thread: report, do not crash
            subscription.lost(failure)

    def _open(self, driver: Driver, key: str) -> SyncRpc:
        """Connect, authenticate and open a channel, reusing a shared socket.

        :param driver: the part of libvirt that serves the call.
        :param key: the channel's key.
        :returns: the ready channel.
        """
        path, rpc = open_channel(
            self._target,
            driver,
            read_only=self._read_only,
            sasl=self._sasl,
            options=self._options,
        )
        shared = self._channels.get(f"path:{path}")
        if shared is not None:
            rpc.close()
            self._channels[key] = shared
            return shared

        self._channels[f"path:{path}"] = rpc
        self._channels[key] = rpc
        return rpc


def convert_arguments(procedure: Procedure[Any, Any], arguments: Any) -> Any:
    """Build the argument struct of a procedure from named values.

    :param procedure: the procedure to call.
    :param arguments: the values by argument name.
    :returns: the argument struct, or ``None`` if the procedure has none.
    :raises ProtocolError: if a name is missing or unknown.
    """
    if procedure.args is None:
        return None

    names = [name for name, _ in procedure.args.xdr_fields]
    if sorted(arguments) != sorted(names):
        raise ProtocolError(f"{procedure.name} takes {names}, got {sorted(arguments)}")

    values = {
        name: _to_wire(xdr_type, arguments[name])
        for name, xdr_type in procedure.args.xdr_fields
    }
    return procedure.args(**values)


def convert_reply(procedure: Procedure[Any, Any], reply: Any) -> Any:
    """Turn a reply struct into the value the operations expect.

    :param procedure: the procedure that was called.
    :param reply: its return struct, or ``None``.
    :returns: ``Handle``s, text, numbers, bytes, typed-parameter dicts,
        ``DomainInfo``, lists of these, or for a reply of several fields the
        generated return struct itself.
    """
    if reply is None:
        return None
    if procedure is procedures.DOMAIN_GET_INFO:
        return _domain_info(reply)
    if procedure is procedures.DOMAIN_GET_STATE:
        return int(reply.state)

    fields = dict(procedure.ret.xdr_fields) if procedure.ret else {}
    names = [name for name in fields if name != "ret" or len(fields) != 2]
    if len(names) != 1:
        return reply
    return _from_wire(getattr(reply, names[0]), fields[names[0]])


def _to_wire(xdr_type: Any, value: Any) -> Any:
    """Convert one argument to what its XDR type holds.

    :param xdr_type: the descriptor of the field.
    :param value: the value the operation gave.
    :returns: the value for the struct.
    :raises ProtocolError: if a handle does not come from a daemon.
    """
    if isinstance(value, Handle):
        return _handle_to_wire(xdr_type, value)
    if isinstance(value, dict) and _is_typed_params(xdr_type):
        return typed_params.to_wire(value)
    if isinstance(xdr_type, xdr.FixedOpaque) and isinstance(value, str):
        return uuid.UUID(value).bytes
    return value


def _handle_to_wire(xdr_type: Any, handle: Handle) -> Any:
    """Convert an object handle to the struct (or name) a field holds.

    :param xdr_type: the descriptor of the field.
    :param handle: the object.
    :returns: the daemon's own struct for the object, or its name for a text field.
    :raises ProtocolError: if the handle was not returned by a daemon.
    """
    if isinstance(xdr_type, xdr.String):
        return handle.name
    if handle.native is None:
        raise ProtocolError(f"{handle!r} does not come from a daemon")
    return handle.native


def _is_typed_params(xdr_type: Any) -> bool:
    """Tell whether a descriptor is a list of typed parameters.

    :param xdr_type: the descriptor of a field.
    :returns: ``True`` for ``remote_typed_param<>``.
    """
    item = getattr(xdr_type, "item", None)
    return isinstance(item, xdr.StructType) and item.cls is types.TypedParam


def _from_wire(value: Any, xdr_type: Any = None) -> Any:
    """Convert a returned value: object structs become handles, parameters dicts.

    :param value: a field of a return struct.
    :param xdr_type: the descriptor of the field, if known.
    :returns: the value for the operations.
    """
    if _is_typed_params(xdr_type):
        return typed_params.from_wire(value)
    if isinstance(value, list):
        return [_from_wire(item) for item in value]
    if type(value).__name__.startswith("Nonnull"):
        return _handle_from_struct(value)
    return value


def _handle_from_struct(struct: Any) -> Handle:
    """Describe a daemon's object struct as a ``Handle``.

    :param struct: a ``Nonnull*`` struct.
    :returns: the handle, which keeps the struct for later requests.
    """
    uuid_bytes = getattr(struct, "uuid", None)
    uuid_text = str(uuid.UUID(bytes=uuid_bytes)) if uuid_bytes else None
    domain_id = getattr(struct, "id", None)
    owner = getattr(struct, "pool", None) or getattr(
        getattr(struct, "dom", None), "name", None
    )
    return Handle(
        name=getattr(struct, "name", None) or uuid_text or "",
        uuid=uuid_text,
        id=domain_id if domain_id is not None and domain_id >= 0 else None,
        parent=owner,
        native=struct,
    )


def _domain_info(reply: types.DomainGetInfoRet) -> DomainInfo:
    """Convert ``remote_domain_get_info_ret``.

    :param reply: the return struct.
    :returns: the information.
    """
    return DomainInfo(
        state=DomainState(reply.state),
        max_memory_kib=reply.max_mem,
        memory_kib=reply.memory,
        vcpus=reply.nr_virt_cpu,
        cpu_time_ns=reply.cpu_time,
    )
