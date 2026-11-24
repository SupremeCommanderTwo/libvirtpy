"""The asyncio twin of ``remote.py``: connecting to a daemon on another host."""

import asyncio
import ssl
from asyncio.subprocess import Process

from libvirtpy.rpc.aio import AsyncRpc
from libvirtpy.rpc.options import ConnectionOptions
from libvirtpy.rpc.remote import (
    CONNECT_TIMEOUT_SECONDS,
    TLS_ACCEPTED,
    ssh_command,
    tls_context,
)
from libvirtpy.rpc.session import ProtocolError
from libvirtpy.rpc.uri import ConnectionTarget

__all__ = ["connect_remote_async"]


async def connect_remote_async(
    target: ConnectionTarget, options: ConnectionOptions | None = None
) -> AsyncRpc:
    """Open a connection to the daemon of a remote target.

    :param target: a target with ``ssh``, ``tls`` or ``tcp`` transport.
    :param options: the call timeout and the keepalive.
    :returns: the connection, before authentication.
    :raises ConnectionError: if the host cannot be reached.
    :raises ProtocolError: if a TLS server rejects our certificate.
    """
    if target.transport == "ssh":
        return await _start_ssh(target, options)
    return await _connect_tcp(target, options)


async def _start_ssh(
    target: ConnectionTarget, options: ConnectionOptions | None
) -> AsyncRpc:
    """Start ``ssh`` and use its pipes.

    :param target: a target with the ``ssh`` transport.
    :param options: the call timeout and the keepalive.
    :returns: the connection.
    :raises ConnectionError: if the ssh program cannot be started.
    """
    command = ssh_command(target)
    try:
        process = await asyncio.create_subprocess_exec(
            *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
        )
    except OSError as error:
        raise ConnectionError(f"cannot start ssh: {error}") from error

    if process.stdin is None or process.stdout is None:
        raise ConnectionError("ssh was started without pipes")

    async def end_process() -> None:
        """End the ``ssh`` process."""
        await _end(process)

    return AsyncRpc(process.stdout, process.stdin, end_process, options)


async def _end(process: Process) -> None:
    """Terminate a process and wait for it.

    :param process: the ``ssh`` process.
    """
    if process.returncode is None:
        process.terminate()
    await process.wait()


async def _connect_tcp(
    target: ConnectionTarget, options: ConnectionOptions | None
) -> AsyncRpc:
    """Connect to a TCP port, with TLS if the transport asks for it.

    :param target: a target with the ``tls`` or ``tcp`` transport.
    :param options: the call timeout and the keepalive.
    :returns: the connection.
    :raises ConnectionError: if the host cannot be reached or TLS fails.
    :raises ProtocolError: if a TLS server does not accept our certificate.
    """
    context = tls_context(target) if target.transport == "tls" else None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                target.host,
                target.port,
                ssl=context,
                server_hostname=target.host if context else None,
            ),
            CONNECT_TIMEOUT_SECONDS,
        )
        accepted = await reader.readexactly(1) if context else TLS_ACCEPTED
    except (TimeoutError, ssl.SSLError, OSError, asyncio.IncompleteReadError) as error:
        raise ConnectionError(
            f"cannot reach {target.host}:{target.port}: {error!r}"
        ) from error

    if accepted != TLS_ACCEPTED:
        writer.close()
        raise ProtocolError("the server did not accept our client certificate")
    return AsyncRpc(reader, writer, options=options)
