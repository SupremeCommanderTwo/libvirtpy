"""A lost connection is opened again, if the client was asked to."""

import asyncio
import time
from collections.abc import Callable, Iterator
from typing import TypedDict

import pytest

from libvirtpy.client import AsyncLibvirtClient, LibvirtClient
from libvirtpy.rpc.session import ConnectionLostError
from tests.helpers.running_server import RunningServer


class Reconnecting(TypedDict):
    """Keyword arguments of ``open`` that turn the reconnect on, with short waits."""

    reconnect: bool
    reconnect_attempts: int
    reconnect_delay: float


FAST = Reconnecting(reconnect=True, reconnect_attempts=3, reconnect_delay=0.05)


@pytest.fixture
def server() -> Iterator[RunningServer]:
    running = RunningServer(None)
    yield running
    running.close()


def uri_of(server: RunningServer) -> str:
    return f"qemu+tcp://127.0.0.1:{server.port}/system"


def wait_for(condition: Callable[[], object], seconds: float = 3.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert condition()


def test_without_the_option_a_lost_connection_stays_lost(
    server: RunningServer,
) -> None:
    with LibvirtClient.open(uri_of(server)) as client:
        assert client.get_hostname()
        server.drop_connections()
        time.sleep(0.2)

        with pytest.raises(ConnectionLostError):
            client.get_hostname()

    assert len(server.daemon.opened) == 1


def test_the_next_call_after_a_lost_connection_reconnects(
    server: RunningServer,
) -> None:
    with LibvirtClient.open(uri_of(server), **FAST) as client:
        first = client.get_hostname()
        server.drop_connections()
        time.sleep(0.2)

        second = client.get_hostname()

    assert first == second
    assert len(server.daemon.opened) == 2


def test_reconnecting_gives_up_after_the_attempts(server: RunningServer) -> None:
    with LibvirtClient.open(uri_of(server), **FAST) as client:
        client.get_hostname()
        server.close()
        server.drop_connections()
        time.sleep(0.2)

        with pytest.raises(ConnectionError, match="cannot reconnect after 3 attempts"):
            client.get_hostname()


def test_a_closed_client_does_not_reconnect(server: RunningServer) -> None:
    client = LibvirtClient.open(uri_of(server), **FAST)
    client.close()

    with pytest.raises(ConnectionLostError, match="closed"):
        client.get_hostname()

    assert len(server.daemon.opened) == 1


def test_a_subscription_goes_on_after_a_reconnect(server: RunningServer) -> None:
    with (
        LibvirtClient.open(uri_of(server), **FAST) as client,
        client.events() as events,
    ):
        wait_for(lambda: len(server.daemon.registered) == 1)
        server.drop_connections()
        wait_for(lambda: len(server.daemon.registered) == 2)
        wait_for(lambda: events.reconnects == 1)

        new_id = max(server.daemon.registered)
        server.daemon.push_lifecycle(new_id, "after", event=2)
        event = events.get(timeout=3)

    assert event.name == "after"


def test_a_subscription_ends_when_the_reconnect_fails(server: RunningServer) -> None:
    with (
        LibvirtClient.open(uri_of(server), **FAST) as client,
        client.events() as events,
    ):
        wait_for(lambda: len(server.daemon.registered) == 1)
        server.close()
        server.drop_connections()

        with pytest.raises(ConnectionError, match="cannot reconnect"):
            events.get(timeout=5)


def test_async_next_call_reconnects(server: RunningServer) -> None:
    async def scenario() -> tuple[str, str]:
        async with await AsyncLibvirtClient.open(uri_of(server), **FAST) as client:
            first = await client.get_hostname()
            server.drop_connections()
            await asyncio.sleep(0.2)
            return first, await client.get_hostname()

    first, second = asyncio.run(scenario())

    assert first == second
    assert len(server.daemon.opened) == 2


def test_async_subscription_goes_on_after_a_reconnect(server: RunningServer) -> None:
    async def scenario() -> str | None:
        async with (
            await AsyncLibvirtClient.open(uri_of(server), **FAST) as client,
            await client.events() as events,
        ):
            while len(server.daemon.registered) < 1:
                await asyncio.sleep(0.01)
            server.drop_connections()
            while len(server.daemon.registered) < 2:
                await asyncio.sleep(0.01)
            while events.reconnects < 1:
                await asyncio.sleep(0.01)

            server.daemon.push_lifecycle(
                max(server.daemon.registered), "after", event=2
            )
            return (await events.get(timeout=3)).name

    assert asyncio.run(scenario()) == "after"


def test_async_reconnecting_gives_up_after_the_attempts(
    server: RunningServer,
) -> None:
    async def scenario() -> None:
        async with await AsyncLibvirtClient.open(uri_of(server), **FAST) as client:
            await client.get_hostname()
            server.close()
            server.drop_connections()
            await asyncio.sleep(0.2)

            with pytest.raises(ConnectionError, match="cannot reconnect"):
                await client.get_hostname()

    asyncio.run(scenario())


def test_waits_double_from_the_first_retry_and_stop_at_the_ceiling() -> None:
    from libvirtpy.rpc.options import ConnectionOptions

    options = ConnectionOptions(reconnect_attempts=8, reconnect_delay=4.0)

    assert options.reconnect_waits() == [0.0, 4.0, 8.0, 16.0, 30.0, 30.0, 30.0, 30.0]
    assert ConnectionOptions(reconnect_attempts=1).reconnect_waits() == [0.0]
    assert not ConnectionOptions().reconnects
