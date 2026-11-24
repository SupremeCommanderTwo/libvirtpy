"""Data streams: download, upload, console and screenshot, sync and async."""

import asyncio
import io
import threading
import time

import pytest

from libvirtpy.client import AsyncLibvirtClient, LibvirtClient
from libvirtpy.rpc.errors import LibvirtError
from libvirtpy.rpc.protocol import procedures, types
from libvirtpy.rpc.session import ConnectionLostError, Session
from tests.helpers.running_server import RunningServer


def wait_until(condition: object, seconds: float = 3.0) -> None:
    """Wait for a condition to become true."""
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:  # type: ignore[operator]
        time.sleep(0.01)
    assert condition()  # type: ignore[operator]


def open_client(server: RunningServer) -> LibvirtClient:
    """Connect a blocking client to a fake daemon."""
    return LibvirtClient.open(f"qemu+tcp://127.0.0.1:{server.port}/system")


def test_session_turns_stream_packets_into_events() -> None:
    session = Session()
    serial, _ = session.call(
        procedures.DOMAIN_OPEN_CONSOLE, _console_args(), stream=True
    )
    data = session.stream_data(serial, b"x")
    session.feed(_inbound(serial, 2, b"abc") + _inbound(serial, 2, b""))

    kinds = [(event.kind, event.data) for event in session.take_stream_events()]
    finish = session.stream_finish(serial)
    session.feed(_inbound(serial, 0, b""))

    assert kinds == [("data", b"abc"), ("end", b"")]
    assert data and finish  # the stream stays open after the daemon's end of data
    assert [e.kind for e in session.take_stream_events()] == ["closed"]
    assert session.stream_data(serial, b"y") == b""  # and is over now


def test_session_ignores_packets_of_unknown_streams() -> None:
    session = Session()

    session.feed(_inbound(99, 2, b"abc"))

    assert session.take_stream_events() == []


def _console_args() -> types.DomainOpenConsoleArgs:
    """Make the arguments of a console call."""
    domain = types.NonnullDomain(name="vm", uuid=bytes(16), id=1)
    return types.DomainOpenConsoleArgs(dom=domain, dev_name=None, flags=0)


def _inbound(serial: int, status: int, payload: bytes) -> bytes:
    """Make a stream packet as a daemon sends it."""
    header = types.VirNetMessageHeader(
        prog=types.REMOTE_PROGRAM,
        vers=types.REMOTE_PROTOCOL_VERSION,
        proc=procedures.DOMAIN_OPEN_CONSOLE.number,
        type=types.VirNetMessageType.STREAM,
        serial=serial,
        status=types.VirNetMessageStatus(status),
    )
    from libvirtpy.rpc import xdr

    body = xdr.encode(xdr.StructType(types.VirNetMessageHeader), header) + payload
    return (4 + len(body)).to_bytes(4, "big") + body


def test_download_reads_everything_the_daemon_sends() -> None:
    server = RunningServer(None)
    try:
        with (
            open_client(server) as client,
            client.download_pool_volume("pool", "disk") as source,
        ):
            data = source.read()

        assert data == b"hello world"
    finally:
        server.close()


def test_download_reads_return_at_most_what_was_asked() -> None:
    server = RunningServer(None)
    try:
        with (
            open_client(server) as client,
            client.download_pool_volume("pool", "disk") as source,
        ):
            pieces = []
            while piece := source.read(4):
                pieces.append(piece)

        assert all(len(piece) <= 4 for piece in pieces)
        assert b"".join(pieces) == b"hello world"
    finally:
        server.close()


def test_download_wrapped_in_a_buffered_reader_returns_exact_sizes() -> None:
    server = RunningServer(None)
    try:
        with open_client(server) as client:
            buffered = io.BufferedReader(client.download_pool_volume("pool", "disk"))

            pieces = [buffered.read(4) for _ in range(4)]
            buffered.close()

        assert pieces == [b"hell", b"o wo", b"rld", b""]
    finally:
        server.close()


def test_download_is_a_binary_file_object() -> None:
    server = RunningServer(None)
    try:
        with (
            open_client(server) as client,
            client.download_pool_volume("pool", "disk") as source,
        ):
            copy = io.BytesIO()
            while chunk := source.read(5):
                copy.write(chunk)

        assert isinstance(source, io.RawIOBase)
        assert copy.getvalue() == b"hello world"
    finally:
        server.close()


def test_a_failure_in_the_middle_of_a_download_is_raised() -> None:
    server = RunningServer(None)
    try:
        with open_client(server) as client:
            stream = client.download_pool_volume("pool", "broken")

            with pytest.raises(LibvirtError, match="fell over"):
                stream.read()
    finally:
        server.close()


def test_closing_a_download_early_aborts_it() -> None:
    server = RunningServer(None)
    try:
        with open_client(server) as client:
            stream = client.download_pool_volume("pool", "slow")
            stream.read(1)

            stream.close()

            wait_until(lambda: server.daemon.aborted)
    finally:
        server.close()


def test_upload_sends_the_data_and_waits_for_the_daemon_to_confirm() -> None:
    server = RunningServer(None)
    try:
        with open_client(server) as client:
            with client.upload_pool_volume("pool", "disk", 0, 11) as target:
                target.write(b"hello ")
                target.write(b"world")

            assert server.daemon.uploaded == b"hello world"
    finally:
        server.close()


def test_a_big_upload_is_sent_in_pieces() -> None:
    server = RunningServer(None)
    data = bytes(range(256)) * 2000
    try:
        with (
            open_client(server) as client,
            client.upload_pool_volume("pool", "disk") as target,
        ):
            assert target.write(data) == len(data)

        assert server.daemon.uploaded == data
    finally:
        server.close()


def test_a_download_stream_cannot_be_written() -> None:
    server = RunningServer(None)
    try:
        with (
            open_client(server) as client,
            client.download_pool_volume("pool", "disk") as source,
            pytest.raises(io.UnsupportedOperation),
        ):
            source.write(b"x")
    finally:
        server.close()


def test_an_upload_stream_cannot_be_read() -> None:
    server = RunningServer(None)
    try:
        with (
            open_client(server) as client,
            client.upload_pool_volume("pool", "disk") as target,
            pytest.raises(io.UnsupportedOperation),
        ):
            target.read()
    finally:
        server.close()


def test_console_is_a_two_way_stream() -> None:
    server = RunningServer(None)
    try:
        with open_client(server) as client, client.open_domain_console("vm") as console:
            console.write(b"hello")

            assert console.read(5) == b"HELLO"
    finally:
        server.close()


def test_screenshot_stream_carries_the_mime_type() -> None:
    server = RunningServer(None)
    try:
        with (
            open_client(server) as client,
            client.take_domain_screenshot("vm") as image,
        ):
            assert image.reply == "image/png"
            assert image.read() == b"hello world"
    finally:
        server.close()


def test_losing_the_connection_ends_a_reading_stream_with_an_error() -> None:
    server = RunningServer(None)
    try:
        client = open_client(server)
        stream = client.open_domain_console("vm")
        result: list[BaseException] = []

        def read() -> None:
            try:
                stream.read(1)
            except BaseException as error:  # recorded for the assert
                result.append(error)

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        time.sleep(0.1)
        client.close()
        reader.join(timeout=5)

        assert result
        assert isinstance(result[0], ConnectionLostError)
    finally:
        server.close()


def test_async_download_and_iteration() -> None:
    server = RunningServer(None)

    async def scenario() -> tuple[bytes, list[bytes]]:
        uri = f"qemu+tcp://127.0.0.1:{server.port}/system"
        async with await AsyncLibvirtClient.open(uri) as client:
            async with await client.download_pool_volume("pool", "disk") as source:
                everything = await source.read()
            async with await client.download_pool_volume("pool", "disk") as source:
                pieces = [piece async for piece in source]
        return everything, pieces

    try:
        everything, pieces = asyncio.run(scenario())

        assert everything == b"hello world"
        assert b"".join(pieces) == b"hello world"
    finally:
        server.close()


def test_async_upload_and_console() -> None:
    server = RunningServer(None)

    async def scenario() -> bytes:
        uri = f"qemu+tcp://127.0.0.1:{server.port}/system"
        async with await AsyncLibvirtClient.open(uri) as client:
            async with await client.upload_pool_volume("pool", "disk") as target:
                await target.write(b"async data")
            async with await client.open_domain_console("vm") as console:
                await console.write(b"ping")
                return await console.read(4)

    try:
        assert asyncio.run(scenario()) == b"PING"
        assert server.daemon.uploaded == b"async data"
    finally:
        server.close()


def test_async_error_in_a_download_is_raised() -> None:
    server = RunningServer(None)

    async def scenario() -> None:
        uri = f"qemu+tcp://127.0.0.1:{server.port}/system"
        async with await AsyncLibvirtClient.open(uri) as client:
            stream = await client.download_pool_volume("pool", "broken")
            await stream.read()

    try:
        with pytest.raises(LibvirtError, match="fell over"):
            asyncio.run(scenario())
    finally:
        server.close()
