"""The asyncio twin of ``wire.py``: operations carried to real daemons."""

import asyncio
from collections.abc import Iterable
from enum import IntEnum
from pathlib import Path

from libvirtpy.client.subscribing import (
    SubscriptionPlan,
    event_lookup,
    plan_subscription,
)
from libvirtpy.client.transport import Request
from libvirtpy.client.wire import PROCEDURES_BY_NAME, convert_arguments, convert_reply
from libvirtpy.rpc.aio import AsyncRpc
from libvirtpy.rpc.errors import ErrorNumber, NotSupportedError
from libvirtpy.rpc.options import ConnectionOptions
from libvirtpy.rpc.procedure import Driver
from libvirtpy.rpc.protocol import procedures
from libvirtpy.rpc.remote_aio import connect_remote_async
from libvirtpy.rpc.sasl import SaslCredentials
from libvirtpy.rpc.session import ConnectionLostError
from libvirtpy.rpc.sockets import (
    REMOTE_KEY,
    authentication,
    open_arguments,
    socket_paths,
)
from libvirtpy.rpc.stream import AsyncRemoteStream
from libvirtpy.rpc.subscription import DEFAULT_MAX_EVENTS, AsyncSubscription
from libvirtpy.rpc.uri import ConnectionTarget, parse_uri

__all__ = ["AsyncWireTransport"]


class AsyncWireTransport:
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

        self._channels: dict[str, AsyncRpc] = {}
        self._by_path: dict[str, AsyncRpc] = {}
        self._opening = asyncio.Lock()
        self._closed = False
        self._restoring: set[asyncio.Task[None]] = set()

    @classmethod
    async def from_uri(
        cls,
        uri: str,
        *,
        read_only: bool = False,
        sasl: SaslCredentials | None = None,
        options: ConnectionOptions | None = None,
    ) -> AsyncWireTransport:
        """Create a transport for a libvirt URI, and check that it connects.

        :param uri: e.g. ``qemu:///system``.
        :param read_only: use the read-only sockets.
        :param sasl: the user name and password, if the daemon asks for SASL.
        :param options: the call timeout, keepalive and reconnect settings.
        :returns: the transport, with the hypervisor channel already open.
        :raises ConnectionError: if the daemon cannot be reached.
        """
        transport = cls(parse_uri(uri), read_only=read_only, sasl=sasl, options=options)
        await transport._channel("hypervisor")
        return transport

    async def call(self, request: Request) -> object:
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
        channel = await self._channel(procedure.driver)
        if request.stream is not None:
            stream = AsyncRemoteStream(channel, request.stream)
            reply = await channel.call(procedure, args, stream=stream)
            stream.reply = convert_reply(procedure, reply)
            return stream
        return convert_reply(procedure, await channel.call(procedure, args))

    async def subscribe(
        self,
        source: str,
        kinds: Iterable[IntEnum] | None,
        target: object,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> AsyncSubscription:
        """Start receiving events.

        :param source: ``domain``, ``network``, ``pool``, ``node_device`` or ``secret``.
        :param kinds: which events; ``None`` for the ``lifecycle`` ones.
        :param target: limit to one object (a reference); ``None`` for all.
        :param max_events: the most events kept for a slow reader.
        :returns: the subscription.
        :raises ValueError: if the source or a kind is unknown.
        """
        plan = plan_subscription(source, kinds)
        handle = (
            None if target is None else await self.call(event_lookup(source, target))
        )
        rpc = await self._channel(plan.register.driver)

        subscription = AsyncSubscription(rpc, plan.deregister, max_events)
        try:
            await self._register(subscription, plan, handle, rpc)
        except Exception:
            await subscription.close()
            raise
        return subscription

    async def close(self) -> None:
        """Close every open channel; the transport does not reconnect after this."""
        self._closed = True
        for task in list(self._restoring):
            task.cancel()
        for channel in set(self._channels.values()):
            await channel.close()
        self._channels.clear()
        self._by_path.clear()

    async def _channel(self, driver: Driver) -> AsyncRpc:
        """Return the channel of a driver, connecting on first use.

        A channel whose connection was lost is replaced by a new one if the
        connection options ask for reconnecting; otherwise it is returned and the
        call on it fails with ``ConnectionLostError``.

        :param driver: the part of libvirt that serves the call.
        :returns: the channel; a remote host or a monolithic ``libvirtd`` shares
            one for all drivers.
        :raises ConnectionLostError: if the transport was closed.
        :raises ConnectionError: if the connection cannot be opened again.
        """
        key = REMOTE_KEY if self._target.remote else driver
        async with self._opening:
            if self._closed:
                raise ConnectionLostError("the client is closed")

            channel = self._channels.get(key)
            if channel is None:
                return await self._opened(driver, key)
            if channel.failure is None or not self._reconnecting():
                return channel

            await self._forget(channel)
            return await self._reopen(driver, key)

    def _reconnecting(self) -> bool:
        """Tell whether lost connections are opened again.

        :returns: ``True`` if the options ask for it.
        """
        return self._options is not None and self._options.reconnects

    async def _opened(self, driver: Driver, key: str) -> AsyncRpc:
        """Open a channel and remember it.

        :param driver: the part of libvirt that serves the call.
        :param key: the channel's key.
        :returns: the ready channel.
        """
        channel = await self._open(driver)
        self._channels[key] = channel
        return channel

    async def _reopen(self, driver: Driver, key: str) -> AsyncRpc:
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
            await asyncio.sleep(wait)
            try:
                return await self._opened(driver, key)
            except (ConnectionError, OSError) as error:
                failure = error
        raise ConnectionError(
            f"cannot reconnect after {len(waits)} attempts: {failure}"
        ) from failure

    async def _forget(self, channel: AsyncRpc) -> None:
        """Drop a dead channel and close what is left of it.

        :param channel: the channel.
        """
        for table in (self._channels, self._by_path):
            for key in [key for key, value in table.items() if value is channel]:
                del table[key]
        await channel.close()

    async def _register(
        self,
        subscription: AsyncSubscription,
        plan: SubscriptionPlan,
        handle: object,
        rpc: AsyncRpc,
    ) -> None:
        """Register the events of a subscription on a connection.

        :param subscription: the subscription.
        :param plan: which registrations to make.
        :param handle: the object to limit to, or ``None``.
        :param rpc: the connection.
        """
        if self._reconnecting():
            rpc.when_lost(
                lambda _error: self._restore_later(subscription, plan, handle)
            )
        else:
            rpc.when_lost(subscription.lost)

        for arguments in plan.arguments(handle):
            await rpc.call(
                plan.register,
                convert_arguments(plan.register, arguments),
                on_result=lambda reply: subscription.attach(reply.callback_id),
            )

    def _restore_later(
        self, subscription: AsyncSubscription, plan: SubscriptionPlan, handle: object
    ) -> None:
        """Start registering a subscription again on a new connection.

        :param subscription: the subscription of the lost connection.
        :param plan: which registrations to make.
        :param handle: the object to limit to, or ``None``.
        """
        task = asyncio.get_running_loop().create_task(
            self._restore(subscription, plan, handle)
        )
        self._restoring.add(task)
        task.add_done_callback(self._restoring.discard)

    async def _restore(
        self, subscription: AsyncSubscription, plan: SubscriptionPlan, handle: object
    ) -> None:
        """Register a subscription again on a new connection.

        :param subscription: the subscription of the lost connection.
        :param plan: which registrations to make.
        :param handle: the object to limit to, or ``None``.
        """
        try:
            rpc = await self._channel(plan.register.driver)
            if subscription.rebind(rpc):
                await self._register(subscription, plan, handle, rpc)
        except asyncio.CancelledError:
            subscription.lost(ConnectionLostError("the client is closed"))
            raise
        except Exception as failure:  # background task: report, do not crash
            subscription.lost(failure)

    async def _open(self, driver: Driver) -> AsyncRpc:
        """Connect, authenticate and open a channel, reusing a shared socket.

        :param driver: the part of libvirt to reach.
        :returns: the ready channel.
        :raises ConnectionError: if no candidate socket accepts a connection.
        """
        path, rpc = await self._connect(driver)
        key = REMOTE_KEY if path is None else str(path)
        shared = self._by_path.get(key)
        if shared is not None:
            await rpc.close()
            return shared

        try:
            await self._authenticate(rpc)
            await rpc.call(
                procedures.CONNECT_OPEN,
                open_arguments(self._target, driver, path, self._read_only),
            )
        except BaseException:
            await rpc.close()  # do not leave the reader task and ssh behind
            raise
        self._by_path[key] = rpc
        return rpc

    async def _authenticate(self, rpc: AsyncRpc) -> None:
        """Do the authentication the daemon asks for.

        :param rpc: a channel that is not opened yet.
        :raises AuthFailedError: if the daemon asks for something we cannot do.
        """
        offered = (await rpc.call(procedures.AUTH_LIST)).types
        steps = authentication(offered, self._target, self._sasl)

        try:
            call = next(steps)
            while True:
                call = steps.send(await rpc.call(*call))
        except StopIteration:
            return

    async def _connect(self, driver: Driver) -> tuple[Path | None, AsyncRpc]:
        """Connect to the daemon of a driver, or to the remote host.

        :param driver: the part of libvirt to reach.
        :returns: the socket path (``None`` if remote) and the connection.
        :raises ConnectionError: if nothing could be reached.
        """
        if self._target.remote:
            return None, await connect_remote_async(self._target, self._options)

        failures = []
        for path in socket_paths(self._target, driver, read_only=self._read_only):
            try:
                return path, await AsyncRpc.connect_unix(path, self._options)
            except OSError as error:
                failures.append(f"{path}: {error.strerror or error}")
        raise ConnectionError("no libvirt socket reachable: " + "; ".join(failures))
