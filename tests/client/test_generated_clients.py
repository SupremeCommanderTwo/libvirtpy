"""The generated clients and proxies pass their arguments to the operations intact.

``client.py`` and ``aio.py`` are generated one-liners. Each method is called with
sample arguments and must send exactly the requests the operation of the same name
sends when it is run on its own; every request is also checked against the real
protocol structures by the synthetic daemon. The proxies are called too.
"""

import asyncio
import inspect
import uuid
from collections.abc import Callable
from typing import Any

import pytest

from libvirtpy.client import AsyncLibvirtClient, LibvirtClient
from libvirtpy.client._runner import run_sync
from libvirtpy.client.transport import Request
from tests.client.test_operations_speak_the_protocol import OPERATIONS, sample_call
from tests.helpers.synthetic_daemon import SyntheticDaemon

PROXY_NAMES = [
    "domain",
    "network",
    "pool",
    "secret",
    "nwfilter",
    "host_interface",
    "node_device",
]
NOT_OPERATIONS = {"open", "close", "events", "lookup"}
REFERENCE = str(uuid.UUID(int=1))  # an object found by UUID: every kind accepts it


class AsyncSyntheticDaemon:
    """The async face of ``SyntheticDaemon``."""

    def __init__(self) -> None:
        """Create a daemon that has served nothing yet."""
        self.daemon = SyntheticDaemon()

    @property
    def requests(self) -> list[Request]:
        """The requests served so far."""
        return self.daemon.requests

    async def call(self, request: Request) -> object:
        """Serve one request."""
        return self.daemon.call(request)

    async def close(self) -> None:
        """Close the connection (nothing to do)."""


def requests_of_operation(
    function: Callable[..., Any], kwargs: dict[str, Any]
) -> list[Request]:
    daemon = SyntheticDaemon()
    run_sync(function(**kwargs), daemon.call)
    return daemon.requests


def test_every_client_method_has_an_operation() -> None:
    public = {
        name
        for name, member in inspect.getmembers(LibvirtClient, inspect.isfunction)
        if not name.startswith("_") and name not in NOT_OPERATIONS
    }
    names = {name for name, _ in OPERATIONS}

    assert public - names <= set(PROXY_NAMES)


@pytest.mark.parametrize(
    ("name", "function"), OPERATIONS, ids=[n for n, _ in OPERATIONS]
)
def test_sync_client_sends_what_the_operation_sends(
    name: str, function: Callable[..., Any]
) -> None:
    kwargs = sample_call(function)
    daemon = SyntheticDaemon()
    client = LibvirtClient(daemon)

    getattr(client, name)(**kwargs)

    assert daemon.requests == requests_of_operation(function, kwargs)


@pytest.mark.parametrize(
    ("name", "function"), OPERATIONS, ids=[n for n, _ in OPERATIONS]
)
def test_async_client_sends_what_the_operation_sends(
    name: str, function: Callable[..., Any]
) -> None:
    kwargs = sample_call(function)
    daemon = AsyncSyntheticDaemon()
    client = AsyncLibvirtClient(daemon)

    asyncio.run(getattr(client, name)(**kwargs))

    assert daemon.requests == requests_of_operation(function, kwargs)


def proxy_methods() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for kind in PROXY_NAMES:
        proxy = type(getattr(LibvirtClient(SyntheticDaemon()), kind)(REFERENCE))
        found.extend(
            (kind, name)
            for name, _ in inspect.getmembers(proxy, inspect.isfunction)
            if not name.startswith("_")
        )
    return found


PROXY_METHODS = proxy_methods()


def test_the_harness_sees_the_proxies() -> None:
    assert len(PROXY_METHODS) >= 100


@pytest.mark.parametrize(
    ("kind", "name"), PROXY_METHODS, ids=[f"{k}.{n}" for k, n in PROXY_METHODS]
)
def test_proxy_method_reaches_the_daemon(kind: str, name: str) -> None:
    daemon = SyntheticDaemon()
    proxy = getattr(LibvirtClient(daemon), kind)(REFERENCE)
    method = getattr(proxy, name)

    method(**sample_call(method))

    assert daemon.requests


@pytest.mark.parametrize(
    ("kind", "name"), PROXY_METHODS, ids=[f"{k}.{n}" for k, n in PROXY_METHODS]
)
def test_async_proxy_method_reaches_the_daemon(kind: str, name: str) -> None:
    daemon = AsyncSyntheticDaemon()
    proxy = getattr(AsyncLibvirtClient(daemon), kind)(REFERENCE)
    method = getattr(proxy, name)

    asyncio.run(method(**sample_call(method)))

    assert daemon.requests
