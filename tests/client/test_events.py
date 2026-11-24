"""Events: decoding what a daemon pushes, and delivering it to subscribers."""

import asyncio
import threading
import time

import pytest

from libvirtpy.client import (
    AsyncLibvirtClient,
    DomainEventKind,
    DomainLifecycle,
    FakeLibvirt,
    LibvirtClient,
    NetworkEventKind,
)
from libvirtpy.rpc.errors import NotSupportedError
from libvirtpy.rpc.events import make_event
from libvirtpy.rpc.session import ConnectionLostError, Session
from tests.helpers.fake_rpc_server import FakeRpcServer
from tests.helpers.running_server import RunningServer


def event_packet(server: FakeRpcServer, callback_id: int) -> bytes:
    """Make the bytes of a lifecycle event, as the server would send them."""
    sent: list[bytes] = []
    server._send = sent.append
    server.push_lifecycle(callback_id, "vm1", event=5, detail=1)
    return sent[0]


def wait_until(condition: object, seconds: float = 3.0) -> None:
    """Wait for a condition to become true."""
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:  # type: ignore[operator]
        time.sleep(0.01)
    assert condition()  # type: ignore[operator]


def test_session_decodes_a_pushed_event_into_an_event() -> None:
    session = Session()

    assert session.feed(event_packet(FakeRpcServer(), 7)) == []
    (pushed,) = session.take_events()
    event = make_event(pushed)

    assert event is not None
    assert (event.source, event.kind, event.name, event.callback_id) == (
        "domain",
        "lifecycle",
        "vm1",
        7,
    )
    assert event.lifecycle == (DomainLifecycle.STOPPED, 1)
    assert session.take_events() == []


def test_the_event_of_a_secret_has_a_uuid_and_no_lifecycle() -> None:
    from libvirtpy.rpc.protocol import procedures, types
    from libvirtpy.rpc.session import ServerEvent

    message = types.SecretEventValueChangedMsg(
        callback_id=3,
        secret=types.NonnullSecret(uuid=bytes(range(16)), usage_type=1, usage_id="/v"),
    )

    event = make_event(ServerEvent(procedures.SECRET_EVENT_VALUE_CHANGED, message))

    assert event is not None
    assert (event.source, event.kind) == ("secret", "value_changed")
    assert event.uuid == "00010203-0405-0607-0809-0a0b0c0d0e0f"
    assert event.lifecycle is None


def test_events_wait_for_a_real_daemon_connection() -> None:
    client = LibvirtClient(FakeLibvirt())

    with pytest.raises(NotSupportedError):
        client.events()


def test_unknown_source_or_kind_is_a_value_error() -> None:
    server = RunningServer(None)
    try:
        with LibvirtClient.open(f"qemu+tcp://127.0.0.1:{server.port}/system") as client:
            with pytest.raises(ValueError, match="source"):
                client.events("cats")
            with pytest.raises(ValueError, match="not an event kind"):
                client.events("domain", [NetworkEventKind.LIFECYCLE])
    finally:
        server.close()


def test_sync_subscription_receives_events_until_closed() -> None:
    server = RunningServer(None)
    try:
        with LibvirtClient.open(f"qemu+tcp://127.0.0.1:{server.port}/system") as client:
            with client.events("domain") as events:
                wait_until(lambda: server.daemon.registered)
                (callback_id,) = server.daemon.registered
                server.daemon.push_lifecycle(callback_id, "vm1", event=2)
                server.daemon.push_lifecycle(callback_id, "vm2", event=5, detail=4)

                first, second = events.get(timeout=3), events.get(timeout=3)

            assert [first.name, second.name] == ["vm1", "vm2"]
            assert first.lifecycle == (DomainLifecycle.STARTED, 0)
            assert server.daemon.registered[callback_id] == DomainEventKind.LIFECYCLE
            wait_until(lambda: server.daemon.deregistered == [callback_id])
    finally:
        server.close()


def test_iteration_ends_when_the_subscription_is_closed() -> None:
    server = RunningServer(None)
    try:
        with LibvirtClient.open(f"qemu+tcp://127.0.0.1:{server.port}/system") as client:
            events = client.events()
            wait_until(lambda: server.daemon.registered)
            (callback_id,) = server.daemon.registered
            server.daemon.push_lifecycle(callback_id, "vm1", event=2)
            seen: list[str] = []

            reader = threading.Thread(
                target=lambda: seen.extend(str(e.name) for e in events), daemon=True
            )
            reader.start()
            wait_until(lambda: seen == ["vm1"])
            events.close()
            reader.join(timeout=3)

            assert not reader.is_alive()
    finally:
        server.close()


def test_get_times_out_when_nothing_happens() -> None:
    server = RunningServer(None)
    try:
        uri = f"qemu+tcp://127.0.0.1:{server.port}/system"
        with (
            LibvirtClient.open(uri) as client,
            client.events() as events,
            pytest.raises(TimeoutError),
        ):
            events.get(timeout=0.1)
    finally:
        server.close()


def test_losing_the_connection_ends_the_subscription_with_an_error() -> None:
    server = RunningServer(None)
    try:
        client = LibvirtClient.open(f"qemu+tcp://127.0.0.1:{server.port}/system")
        events = client.events()
        wait_until(lambda: server.daemon.registered)

        client.close()

        with pytest.raises(ConnectionLostError):
            events.get(timeout=3)
    finally:
        server.close()


def test_the_client_answers_keepalive_pings_while_idle() -> None:
    server = RunningServer(None)
    try:
        with LibvirtClient.open(f"qemu+tcp://127.0.0.1:{server.port}/system") as client:
            client.get_hostname()
            server.daemon.ping()
            server.daemon.ping()

            wait_until(lambda: server.daemon.pongs == 2)
    finally:
        server.close()


def test_calls_from_several_threads_do_not_mix_up_replies() -> None:
    server = RunningServer(None)
    try:
        with LibvirtClient.open(f"qemu+tcp://127.0.0.1:{server.port}/system") as client:
            results: list[str] = []

            def work() -> None:
                results.extend(client.get_hostname() for _ in range(20))

            threads = [threading.Thread(target=work) for _ in range(5)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)

            assert results == ["remote-host"] * 100
    finally:
        server.close()


def test_async_subscription_receives_events() -> None:
    server = RunningServer(None)

    async def scenario() -> list[str]:
        uri = f"qemu+tcp://127.0.0.1:{server.port}/system"
        client = await AsyncLibvirtClient.open(uri)
        async with client, await client.events("domain") as events:
            (callback_id,) = server.daemon.registered
            server.daemon.push_lifecycle(callback_id, "vm1", event=2)
            server.daemon.push_lifecycle(callback_id, "vm2", event=5)
            received = [await events.get(timeout=3), await events.get(timeout=3)]
            return [str(event.name) for event in received]

    try:
        assert asyncio.run(scenario()) == ["vm1", "vm2"]
        wait_until(lambda: len(server.daemon.deregistered) == 1)
    finally:
        server.close()


def test_async_iteration_ends_with_an_error_when_the_connection_drops() -> None:
    server = RunningServer(None)

    async def scenario() -> None:
        uri = f"qemu+tcp://127.0.0.1:{server.port}/system"
        client = await AsyncLibvirtClient.open(uri)
        events = await client.events("domain")
        await client.close()
        async for _ in events:
            pass

    try:
        with pytest.raises(ConnectionLostError):
            asyncio.run(scenario())
    finally:
        server.close()
