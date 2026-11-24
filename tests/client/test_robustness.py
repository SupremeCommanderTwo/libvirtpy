"""A hung or dead daemon: call timeouts, keepalive, late replies."""

import asyncio
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from libvirtpy.client import AsyncLibvirtClient, LibvirtClient
from libvirtpy.rpc.protocol import procedures
from libvirtpy.rpc.session import (
    CallTimeoutError,
    ConnectionLostError,
    ProtocolError,
    Session,
)
from libvirtpy.rpc.subscription import END, EventBuffer
from libvirtpy.rpc.sync import SyncRpc
from tests.helpers.running_server import RunningServer

HOSTNAME_CALL = "connect_get_hostname"


@pytest.fixture
def server() -> Iterator[RunningServer]:
    running = RunningServer(None)
    yield running
    running.close()


def uri_of(server: RunningServer) -> str:
    return f"qemu+tcp://127.0.0.1:{server.port}/system"


def test_a_call_that_gets_no_reply_times_out_and_the_connection_stays_usable(
    server: RunningServer,
) -> None:
    server.daemon.silent = {HOSTNAME_CALL}
    started = time.monotonic()

    with LibvirtClient.open(uri_of(server), timeout=0.3) as client:
        with pytest.raises(CallTimeoutError, match="connect_get_hostname"):
            client.get_hostname()
        elapsed = time.monotonic() - started
        version = client.get_library_version()

    assert elapsed < 3
    assert version > 0


def test_the_late_reply_of_a_timed_out_call_is_dropped_not_a_protocol_error(
    server: RunningServer,
) -> None:
    server.daemon.delayed = {HOSTNAME_CALL: 0.3}

    with LibvirtClient.open(uri_of(server), timeout=0.1) as client:
        with pytest.raises(CallTimeoutError):
            client.get_hostname()
        time.sleep(0.5)
        version = client.get_library_version()

    assert version > 0


def test_without_a_timeout_a_slow_call_just_waits(server: RunningServer) -> None:
    server.daemon.delayed = {HOSTNAME_CALL: 0.4}

    with LibvirtClient.open(uri_of(server)) as client:
        assert client.get_hostname()


def test_an_idle_connection_is_pinged(server: RunningServer) -> None:
    with LibvirtClient.open(uri_of(server), keepalive_interval=0.1) as client:
        time.sleep(0.6)
        assert client.get_library_version() > 0

    assert server.daemon.pings >= 2


def test_the_keepalive_can_be_turned_off(server: RunningServer) -> None:
    with LibvirtClient.open(uri_of(server), keepalive_interval=None) as client:
        time.sleep(0.4)
        assert client.get_library_version() > 0

    assert server.daemon.pings == 0


def test_a_daemon_that_stops_answering_ends_the_waiting_call(
    server: RunningServer,
) -> None:
    server.daemon.silent = {HOSTNAME_CALL}
    server.daemon.answer_pings = False
    started = time.monotonic()

    with LibvirtClient.open(
        uri_of(server), keepalive_interval=0.1, keepalive_count=2
    ) as client:
        with pytest.raises(ConnectionLostError, match="silent"):
            client.get_hostname()
        with pytest.raises(ConnectionLostError):
            client.get_library_version()

    assert time.monotonic() - started < 5


def test_a_busy_daemon_that_still_answers_pings_is_not_given_up(
    server: RunningServer,
) -> None:
    server.daemon.delayed = {HOSTNAME_CALL: 0.5}

    with LibvirtClient.open(
        uri_of(server), keepalive_interval=0.05, keepalive_count=2
    ) as client:
        assert client.get_hostname()


def test_async_call_times_out_and_the_connection_stays_usable(
    server: RunningServer,
) -> None:
    server.daemon.delayed = {HOSTNAME_CALL: 0.3}

    async def scenario() -> int:
        async with await AsyncLibvirtClient.open(uri_of(server), timeout=0.1) as client:
            with pytest.raises(CallTimeoutError):
                await client.get_hostname()
            await asyncio.sleep(0.5)
            return await client.get_library_version()

    assert asyncio.run(scenario()) > 0


def test_async_cancelled_call_does_not_break_the_connection(
    server: RunningServer,
) -> None:
    server.daemon.delayed = {HOSTNAME_CALL: 0.3}

    async def scenario() -> int:
        async with await AsyncLibvirtClient.open(uri_of(server)) as client:
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(client.get_hostname(), 0.1)
            await asyncio.sleep(0.5)
            return await client.get_library_version()

    assert asyncio.run(scenario()) > 0


def test_async_idle_connection_is_pinged_and_a_dead_one_is_given_up(
    server: RunningServer,
) -> None:
    async def scenario() -> None:
        async with await AsyncLibvirtClient.open(
            uri_of(server), keepalive_interval=0.1
        ) as client:
            await asyncio.sleep(0.5)
            assert await client.get_library_version() > 0

        server.daemon.silent = {HOSTNAME_CALL}
        server.daemon.answer_pings = False
        async with await AsyncLibvirtClient.open(
            uri_of(server), keepalive_interval=0.1, keepalive_count=2
        ) as client:
            with pytest.raises(ConnectionLostError, match="silent"):
                await client.get_hostname()

    asyncio.run(scenario())

    assert server.daemon.pings >= 2


def test_session_drops_the_reply_of_an_abandoned_call() -> None:
    session = Session()
    serial, _ = session.call(procedures.CONNECT_GET_VERSION)
    session.abandon(serial)
    reply = _reply(serial)

    assert session.feed(reply) == []
    with pytest.raises(ProtocolError, match="unknown serial"):
        session.feed(_reply(serial))


def _reply(serial: int) -> bytes:
    from libvirtpy.rpc import xdr
    from libvirtpy.rpc.protocol import types

    header = types.VirNetMessageHeader(
        prog=types.REMOTE_PROGRAM,
        vers=types.REMOTE_PROTOCOL_VERSION,
        proc=procedures.CONNECT_GET_VERSION.number,
        type=types.VirNetMessageType.REPLY,
        serial=serial,
        status=types.VirNetMessageStatus.OK,
    )
    body = xdr.encode(xdr.StructType(types.VirNetMessageHeader), header)
    body += xdr.encode(
        xdr.StructType(types.ConnectGetVersionRet),
        types.ConnectGetVersionRet(hv_ver=1),
    )
    return (4 + len(body)).to_bytes(4, "big") + body


def push_many(server: RunningServer, callback_id: int, count: int) -> None:
    for number in range(count):
        server.daemon.push_lifecycle(callback_id, f"vm{number}", event=2)


def wait_for(condition: Callable[[], object], seconds: float = 3.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert condition()


def test_a_slow_reader_loses_the_oldest_events_not_memory(
    server: RunningServer,
) -> None:
    with (
        LibvirtClient.open(uri_of(server)) as client,
        client.events(max_events=10) as events,
    ):
        wait_for(lambda: server.daemon.registered)
        (callback_id,) = server.daemon.registered
        push_many(server, callback_id, 50)
        wait_for(lambda: events.dropped == 40)

        names = [events.get(timeout=2).name for _ in range(10)]

    assert names == [f"vm{number}" for number in range(40, 50)]


def test_async_slow_reader_loses_the_oldest_events(server: RunningServer) -> None:
    async def scenario() -> tuple[list[str | None], int]:
        async with (
            await AsyncLibvirtClient.open(uri_of(server)) as client,
            await client.events(max_events=5) as events,
        ):
            while not server.daemon.registered:
                await asyncio.sleep(0.01)
            (callback_id,) = server.daemon.registered
            push_many(server, callback_id, 20)
            while events.dropped < 15:
                await asyncio.sleep(0.01)

            names = [(await events.get(timeout=2)).name for _ in range(5)]
            return names, events.dropped

    names, dropped = asyncio.run(scenario())

    assert names == [f"vm{number}" for number in range(15, 20)]
    assert dropped == 15


def test_the_end_of_a_subscription_comes_after_its_events_and_stays() -> None:
    buffer = EventBuffer(3)
    buffer.finish(ConnectionLostError("gone"))
    buffer.finish(END)

    first = buffer.take()
    second = buffer.take()

    assert isinstance(first, ConnectionLostError)
    assert second is first


def test_an_empty_buffer_has_nothing_to_take() -> None:
    buffer = EventBuffer(3)

    assert not buffer.ready()
    with pytest.raises(LookupError):
        buffer.take()
    with pytest.raises(ValueError, match="max_events"):
        EventBuffer(0)


def test_garbage_from_the_daemon_fails_the_waiting_call_with_a_protocol_error(
    server: RunningServer,
) -> None:
    server.daemon.silent = {HOSTNAME_CALL}
    garbage = (0x7FFFFFF0).to_bytes(4, "big") + b"x" * 8

    with LibvirtClient.open(uri_of(server)) as client:
        threading.Timer(0.2, server.daemon.write, [garbage]).start()

        with pytest.raises(ProtocolError, match="too big"):
            client.get_hostname()
        with pytest.raises(ProtocolError):
            client.get_library_version()


def test_connecting_to_a_missing_unix_socket_is_an_os_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        SyncRpc.connect_unix(tmp_path / "no-such-socket")
