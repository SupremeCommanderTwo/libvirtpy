"""Finding, opening and authenticating the sockets of libvirt daemons."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

from libvirtpy.rpc.errors import AuthFailedError, ErrorNumber
from libvirtpy.rpc.options import ConnectionOptions
from libvirtpy.rpc.procedure import Driver
from libvirtpy.rpc.protocol import procedures, types
from libvirtpy.rpc.remote import connect_remote
from libvirtpy.rpc.sasl import SaslCall, SaslCredentials, sasl_exchange
from libvirtpy.rpc.sync import SyncRpc
from libvirtpy.rpc.uri import HYPERVISOR_DAEMONS, ConnectionTarget, parse_uri

__all__ = [
    "REMOTE_KEY",
    "ConnectionTarget",
    "authentication",
    "open_arguments",
    "open_channel",
    "parse_uri",
    "socket_paths",
]

SECONDARY_DAEMONS = {
    "interface": ("virtinterfaced", "interface"),
    "network": ("virtnetworkd", "network"),
    "node_device": ("virtnodedevd", "nodedev"),
    "nwfilter": ("virtnwfilterd", "nwfilter"),
    "secret": ("virtsecretd", "secret"),
    "storage": ("virtstoraged", "storage"),
}
CONNECT_READ_ONLY = 1
REMOTE_KEY = "remote"
"""The connection key of a remote target: one connection serves every driver."""


def socket_paths(
    target: ConnectionTarget, driver: Driver, *, read_only: bool
) -> list[Path]:
    """List the sockets that may serve a driver, best first.

    A modular daemon (``virtqemud``) comes first, the monolithic ``libvirtd``
    after it.

    :param target: what the URI asks for.
    :param driver: the part of libvirt that serves the call.
    :param read_only: use the read-only sockets.
    :returns: the candidate paths.
    """
    directory = _socket_directory(target)
    suffix = "-sock-ro" if read_only else "-sock"
    daemon = (
        HYPERVISOR_DAEMONS[target.driver]
        if driver == "hypervisor"
        else SECONDARY_DAEMONS[driver][0]
    )
    return [directory / f"{daemon}{suffix}", directory / f"libvirt{suffix}"]


def open_channel(
    target: ConnectionTarget,
    driver: Driver,
    *,
    read_only: bool,
    sasl: SaslCredentials | None = None,
    options: ConnectionOptions | None = None,
) -> tuple[str, SyncRpc]:
    """Connect to the daemon of a driver, authenticate, and open the connection.

    For a remote target one connection serves every driver.

    :param target: what the URI asks for.
    :param driver: the part of libvirt to reach.
    :param read_only: use the read-only sockets and open the connection read-only.
    :param sasl: the user name and password, if the daemon asks for SASL.
    :param options: the call timeout and the keepalive.
    :returns: a key for the connection (its socket path, or ``remote``) and the
        ready channel.
    :raises ConnectionError: if no candidate socket accepts a connection.
    :raises AuthFailedError: if the daemon asks for an unsupported authentication.
    """
    if target.remote:
        key, rpc = REMOTE_KEY, connect_remote(target, options)
        path = None
    else:
        path, rpc = _connect_first(
            socket_paths(target, driver, read_only=read_only), options
        )
        key = str(path)

    try:
        authenticate(rpc, target, sasl)
        rpc.call(
            procedures.CONNECT_OPEN, open_arguments(target, driver, path, read_only)
        )
    except BaseException:
        rpc.close()  # do not leave the reader thread and the ssh process behind
        raise
    return key, rpc


def authenticate(
    rpc: SyncRpc, target: ConnectionTarget, credentials: SaslCredentials | None
) -> None:
    """Do the authentication the daemon asks for.

    :param rpc: a channel that is not opened yet.
    :param target: what the URI asks for.
    :param credentials: the user name and password for SASL, if we have any.
    :raises AuthFailedError: if the daemon asks for something we cannot do.
    """
    offered = rpc.call(procedures.AUTH_LIST).types
    steps = authentication(offered, target, credentials)

    try:
        call = next(steps)
        while True:
            call = steps.send(rpc.call(*call))
    except StopIteration:
        return


def authentication(
    offered: list[types.AuthType],
    target: ConnectionTarget,
    credentials: SaslCredentials | None,
) -> Generator[SaslCall, Any]:
    """Choose and run the authentication, without doing any I/O.

    :param offered: the methods the daemon accepts.
    :param target: what the URI asks for.
    :param credentials: the user name and password for SASL, if we have any.
    :returns: a generator that yields ``(procedure, arguments)`` and receives the
        reply of each call; it ends at once if no authentication is needed.
    :raises AuthFailedError: if the daemon asks for something we cannot do.
    """
    if types.AuthType.NONE in offered:
        return
    if types.AuthType.POLKIT in offered:
        yield procedures.AUTH_POLKIT, None
        return
    if types.AuthType.SASL in offered:
        yield from _sasl(target, credentials)
        return
    raise _unsupported(offered)


def _sasl(
    target: ConnectionTarget, credentials: SaslCredentials | None
) -> Generator[SaslCall, Any]:
    """Run SASL if it is possible and safe.

    :param target: what the URI asks for.
    :param credentials: the user name and password, if we have any.
    :returns: the SASL conversation.
    :raises AuthFailedError: without credentials, or on a plain TCP connection.
    """
    if credentials is None:
        raise AuthFailedError(
            "the daemon needs SASL credentials: pass sasl=SaslCredentials(...)",
            code=ErrorNumber.AUTH_FAILED,
        )
    if not target.protected:
        raise AuthFailedError(
            "SASL over plain TCP needs a security layer, which is not supported; "
            "use qemu+tls:// or qemu+ssh://",
            code=ErrorNumber.AUTH_FAILED,
        )
    yield from sasl_exchange(credentials, target.host or "localhost")


def _unsupported(offered: list[types.AuthType]) -> AuthFailedError:
    """Make the error for authentication methods we do not know.

    :param offered: the methods the daemon accepts.
    :returns: the exception.
    """
    names = [kind.name for kind in offered]
    return AuthFailedError(
        f"the daemon asks for {names}, which is not supported",
        code=ErrorNumber.AUTH_FAILED,
    )


def open_arguments(
    target: ConnectionTarget, driver: Driver, path: Path | None, read_only: bool
) -> types.ConnectOpenArgs:
    """Build the arguments of ``CONNECT_OPEN`` for a channel.

    A remote daemon is opened with the URI stripped of transport and host. A
    secondary modular daemon is opened with its own URI scheme
    (``network:///system``); the primary one and ``libvirtd`` with the user's URI.

    :param target: what the URI asks for.
    :param driver: the part of libvirt the channel serves.
    :param path: the socket the channel is connected to; ``None`` if remote.
    :param read_only: open the connection read-only.
    :returns: the arguments.
    """
    flags = CONNECT_READ_ONLY if read_only else 0
    if path is None:
        return types.ConnectOpenArgs(name=target.open_name, flags=flags)

    is_secondary = driver != "hypervisor" and not path.name.startswith("libvirt")
    name = _secondary_uri(target, driver) if is_secondary else target.uri
    return types.ConnectOpenArgs(name=name, flags=flags)


def _connect_first(
    paths: list[Path], options: ConnectionOptions | None
) -> tuple[Path, SyncRpc]:
    """Connect to the first socket that answers.

    :param paths: the candidates.
    :param options: the call timeout and the keepalive.
    :returns: the path and the connection.
    :raises ConnectionError: if none could be reached.
    """
    failures = []
    for path in paths:
        try:
            return path, SyncRpc.connect_unix(path, options)
        except OSError as error:
            failures.append(f"{path}: {error.strerror or error}")
    raise ConnectionError("no libvirt socket reachable: " + "; ".join(failures))


def _secondary_uri(target: ConnectionTarget, driver: Driver) -> str:
    """Build the URI a secondary daemon is opened with.

    :param target: what the URI asks for.
    :param driver: a secondary driver (``network``, ``storage``, ...).
    :returns: e.g. ``network:///system``.
    """
    scheme = SECONDARY_DAEMONS[driver][1]
    return f"{scheme}:///{'session' if target.session else 'system'}"


def _socket_directory(target: ConnectionTarget) -> Path:
    """Find the directory of the daemon sockets.

    :param target: what the URI asks for.
    :returns: ``/run/libvirt`` or the user's runtime directory.
    """
    if not target.session:
        return Path("/run/libvirt")
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(runtime) / "libvirt"
