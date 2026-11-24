"""Operations that open a data stream: console, screenshot, volume upload/download.

They return an open stream (``RemoteStream`` in the blocking client,
``AsyncRemoteStream`` in the async one) that you read or write and then close.
"""

from typing import cast

from libvirtpy.client.operations._common import one_handle
from libvirtpy.client.references import (
    DomainRef,
    PoolRef,
    VolumeRef,
    domain_lookup,
    pool_lookup,
    volume_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.rpc.stream import AsyncRemoteStream, Mode, RemoteStream

__all__ = [
    "download_pool_volume",
    "open_domain_channel",
    "open_domain_console",
    "take_domain_screenshot",
    "upload_pool_volume",
]


def open_domain_console(
    domain: DomainRef, device: str | None = None, *, flags: int = 0
) -> Operation[RemoteStream]:
    """Open the text console of a domain, to read its output and type into it.

    :param domain: the domain; it must be running.
    :param device: the console or serial device alias (``serial0``); ``None`` for
        the first one.
    :param flags: ``virDomainConsoleFlags``: 1 force (take it from another client),
        2 safe.
    :returns: a stream you read and write; close it to disconnect.
    """
    return _stream(
        (
            yield from _open(
                domain, "domain_open_console", "both", dev_name=device, flags=flags
            )
        )
    )


def open_domain_channel(
    domain: DomainRef, name: str | None = None, *, flags: int = 0
) -> Operation[RemoteStream]:
    """Open a named channel to the guest (for example the guest agent channel).

    :param domain: the domain; it must be running.
    :param name: the channel name; ``None`` for the first one.
    :param flags: ``virDomainChannelFlags``: 1 force.
    :returns: a stream you read and write; close it to disconnect.
    """
    return _stream(
        (
            yield from _open(
                domain, "domain_open_channel", "both", name=name, flags=flags
            )
        )
    )


def take_domain_screenshot(
    domain: DomainRef, screen: int = 0, *, flags: int = 0
) -> Operation[RemoteStream]:
    """Take a screenshot of a running domain.

    :param domain: the domain.
    :param screen: which screen, for a domain with several.
    :param flags: reserved, 0.
    :returns: a stream to read the image from; its ``reply`` is the MIME type
        (e.g. ``image/x-portable-pixmap``, or ``image/png``).
    """
    return _stream(
        (
            yield from _open(
                domain, "domain_screenshot", "read", screen=screen, flags=flags
            )
        )
    )


def download_pool_volume(
    pool: PoolRef,
    volume: VolumeRef,
    offset: int = 0,
    length: int = 0,
    *,
    flags: int = 0,
) -> Operation[RemoteStream]:
    """Read the contents of a volume.

    :param pool: the pool.
    :param volume: the volume.
    :param offset: where to start, in bytes.
    :param length: how many bytes; 0 for everything from ``offset``.
    :param flags: ``virStorageVolDownloadFlags``.
    :returns: a stream to read the bytes from.
    """
    reply = yield from _on_volume(
        pool, volume, "storage_vol_download", "read", offset, length, flags
    )
    return _stream(reply)


def upload_pool_volume(
    pool: PoolRef,
    volume: VolumeRef,
    offset: int = 0,
    length: int = 0,
    *,
    flags: int = 0,
) -> Operation[RemoteStream]:
    """Write bytes into a volume.

    :param pool: the pool.
    :param volume: the volume; it must already exist and be big enough.
    :param offset: where to start, in bytes.
    :param length: how many bytes you will write; 0 for the rest of the volume.
    :param flags: ``virStorageVolUploadFlags``.
    :returns: a stream to write the bytes to; close it to finish the upload.
    """
    reply = yield from _on_volume(
        pool, volume, "storage_vol_upload", "write", offset, length, flags
    )
    return _stream(reply)


def _open(
    domain: DomainRef, procedure: str, mode: Mode, **arguments: object
) -> Operation[object]:
    """Call a procedure of a domain that opens a stream.

    :param domain: the domain.
    :param procedure: the procedure.
    :param mode: which way the data flows: ``read``, ``write`` or ``both``.
    :param arguments: the arguments of the procedure other than the domain.
    :returns: the open stream.
    """
    handle = yield from _handle_of(domain)
    request = Request(procedure, {"dom": handle, **arguments}, stream=mode)
    return (yield request)


def _on_volume(
    pool: PoolRef,
    volume: VolumeRef,
    procedure: str,
    mode: Mode,
    offset: int,
    length: int,
    flags: int,
) -> Operation[object]:
    """Call a procedure of a volume that opens a stream.

    :param pool: the pool.
    :param volume: the volume.
    :param procedure: the procedure.
    :param mode: which way the data flows.
    :param offset: where to start, in bytes.
    :param length: how many bytes.
    :param flags: the flags of the call.
    :returns: the open stream.
    """
    pool_handle = yield from one_handle(pool_lookup(pool))
    volume_handle = yield from one_handle(volume_lookup(pool_handle, volume))
    arguments = {
        "vol": volume_handle,
        "offset": offset,
        "length": length,
        "flags": flags,
    }
    return (yield Request(procedure, arguments, stream=mode))


def _handle_of(domain: DomainRef) -> Operation[object]:
    """Find a domain.

    :param domain: the domain.
    :returns: its handle.
    """
    return (yield from one_handle(domain_lookup(domain)))


def _stream(reply: object) -> RemoteStream:
    """Check that a reply is an open stream.

    :param reply: what the transport returned.
    :returns: the stream (an ``AsyncRemoteStream`` for the async client).
    :raises TypeError: if it is not a stream.
    """
    if not isinstance(reply, RemoteStream | AsyncRemoteStream):
        raise TypeError(f"expected a stream, got {reply!r}")
    return cast(RemoteStream, reply)
