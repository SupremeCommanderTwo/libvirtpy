"""Connecting to a libvirt daemon on another host: SSH, TLS or plain TCP.

The pure parts (the ``ssh`` command line, the TLS settings) are separate
functions so that ``remote_aio`` shares them.
"""

import contextlib
import os
import shlex
import socket
import ssl
import subprocess
from pathlib import Path

from libvirtpy.rpc.options import ConnectionOptions
from libvirtpy.rpc.session import ConnectionLostError, ProtocolError
from libvirtpy.rpc.sync import SocketStream, Stream, SyncRpc
from libvirtpy.rpc.uri import ConnectionTarget

__all__ = [
    "ProcessStream",
    "TlsFiles",
    "connect_remote",
    "ssh_command",
    "tls_context",
    "tls_files",
]

CONNECT_TIMEOUT_SECONDS = 30
DEFAULT_REMOTE_SOCKET = "/var/run/libvirt/libvirt-sock"
TLS_ACCEPTED = b"\x01"
"""The byte a server sends when it has accepted the client certificate."""


class TlsFiles:
    """The certificate files of a TLS connection."""

    def __init__(self, ca: Path, certificate: Path, key: Path) -> None:
        """Remember the three paths.

        :param ca: the certificate authority that signed the server certificate.
        :param certificate: our client certificate.
        :param key: the private key of the client certificate.
        """
        self.ca = ca
        self.certificate = certificate
        self.key = key


class ProcessStream:
    """A ``Stream`` over the standard input and output of a child process."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        """Wrap a process started with both pipes.

        :param process: the process, e.g. ``ssh host virt-ssh-helper``.
        """
        self._process = process

    def send(self, data: bytes) -> None:
        """Send all of ``data`` to the process.

        :param data: the bytes.
        :raises ProtocolError: if the process has gone away.
        """
        stdin = self._process.stdin
        if stdin is None:
            raise ProtocolError("the process has no standard input")
        try:
            stdin.write(data)
            stdin.flush()
        except BrokenPipeError as error:
            raise ConnectionLostError(
                "the ssh process closed the connection"
            ) from error

    def receive(self) -> bytes:
        """Wait for bytes from the process.

        :returns: some bytes, or nothing at its end.
        :raises ProtocolError: if the process has no standard output.
        """
        stdout = self._process.stdout
        if stdout is None:
            raise ProtocolError("the process has no standard output")
        return stdout.read1(65536)  # type: ignore[attr-defined,no-any-return]  # BufferedReader has read1; Popen types it as IO[bytes]

    def close(self) -> None:
        """End the process; a thread reading its output sees the end of the file."""
        self._process.terminate()
        self._process.wait()
        for pipe in (self._process.stdin, self._process.stdout):
            if pipe is not None:
                with contextlib.suppress(OSError, ValueError):
                    pipe.close()


def connect_remote(
    target: ConnectionTarget, options: ConnectionOptions | None = None
) -> SyncRpc:
    """Open a connection to the daemon of a remote target.

    :param target: a target with ``ssh``, ``tls`` or ``tcp`` transport.
    :param options: the call timeout and the keepalive.
    :returns: the connection, before authentication.
    :raises ConnectionError: if the host cannot be reached.
    :raises ProtocolError: if a TLS server rejects our certificate.
    """
    if target.transport == "ssh":
        return SyncRpc(_start_ssh(target), options)
    return SyncRpc(_connect_tcp(target), options)


def ssh_command(target: ConnectionTarget) -> list[str]:
    """Build the ``ssh`` command that reaches the daemon of a host.

    URI parameters, as in libvirt: ``command`` (the ssh program), ``keyfile``,
    ``proxy`` (``auto``, ``native`` for ``virt-ssh-helper``, ``netcat``),
    ``socket`` and ``netcat`` (for the netcat proxy), ``no_tty``,
    ``known_hosts_verify`` (``ignore``).

    :param target: a target with the ``ssh`` transport.
    :returns: the program and its arguments; the last one is the command that the
        remote shell runs.
    :raises ValueError: if ``proxy`` is not one of the known values.
    """
    parameters = target.parameters
    command = [parameters.get("command", "ssh"), "-T", "-e", "none"]

    if target.port is not None:
        command += ["-p", str(target.port)]
    if parameters.get("keyfile"):
        command += ["-i", parameters["keyfile"]]
    if parameters.get("no_tty") == "1":
        command += ["-o", "BatchMode=yes"]
    if parameters.get("known_hosts_verify") == "ignore":
        command += ["-o", "StrictHostKeyChecking=no"]

    destination = f"{target.user}@{target.host}" if target.user else str(target.host)
    # ssh joins its arguments with spaces and the remote login shell parses the
    # result again, so the script must reach it as one quoted word
    remote_command = f"sh -c {shlex.quote(_remote_script(target))}"
    return [*command, destination, remote_command]


def tls_files(target: ConnectionTarget) -> TlsFiles:
    """Find the certificate files, as libvirt does.

    ``pkipath`` names one directory with ``cacert.pem``, ``clientcert.pem`` and
    ``clientkey.pem``; ``~`` and ``$VARIABLES`` in it are expanded, so a quoted
    ``?pkipath=$HOME/.pki/x`` works. Otherwise root uses ``/etc/pki`` and others
    ``~/.pki/libvirt``.

    :param target: a target with the ``tls`` transport.
    :returns: the three paths.
    """
    pki_path = target.parameters.get("pkipath")
    if pki_path:
        directory = Path(os.path.expandvars(pki_path)).expanduser()
        return TlsFiles(
            directory / "cacert.pem",
            directory / "clientcert.pem",
            directory / "clientkey.pem",
        )

    if os.geteuid() == 0:
        return TlsFiles(
            Path("/etc/pki/CA/cacert.pem"),
            Path("/etc/pki/libvirt/clientcert.pem"),
            Path("/etc/pki/libvirt/private/clientkey.pem"),
        )

    home = Path.home() / ".pki" / "libvirt"
    return TlsFiles(
        home / "cacert.pem", home / "clientcert.pem", home / "clientkey.pem"
    )


def tls_context(target: ConnectionTarget) -> ssl.SSLContext:
    """Build the TLS settings of a connection.

    ``no_verify=1`` accepts any server certificate, like libvirt. Without
    ``pkipath``, a missing CA file falls back to the system's trusted CAs; with
    it, a missing CA file is an error, because the user named the directory.

    :param target: a target with the ``tls`` transport.
    :returns: the client context, with our certificate loaded if the files exist.
    :raises ConnectionError: if ``pkipath`` is given and has no ``cacert.pem``.
    """
    files = tls_files(target)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    if target.parameters.get("no_verify") == "1":
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    elif files.ca.exists():
        context.load_verify_locations(cafile=str(files.ca))
    elif target.parameters.get("pkipath"):
        raise ConnectionError(f"pkipath: no CA certificate at {files.ca}")
    else:
        context.load_default_certs()

    if files.certificate.exists() and files.key.exists():
        context.load_cert_chain(str(files.certificate), str(files.key))
    return context


def _remote_script(target: ConnectionTarget) -> str:
    """Build the shell script run on the remote host.

    :param target: a target with the ``ssh`` transport.
    :returns: a script that connects its standard input and output to the daemon.
    :raises ValueError: if ``proxy`` is unknown.
    """
    parameters = target.parameters
    helper = f"exec virt-ssh-helper {shlex.quote(target.open_name)}"
    netcat = "exec {} -U {}".format(
        shlex.quote(parameters.get("netcat", "nc")),
        shlex.quote(parameters.get("socket", DEFAULT_REMOTE_SOCKET)),
    )

    proxy = parameters.get("proxy", "auto")
    if proxy == "native":
        return helper
    if proxy == "netcat":
        return netcat
    if proxy == "auto":
        return (
            f"if type virt-ssh-helper >/dev/null 2>&1; then {helper}; else {netcat}; fi"
        )
    raise ValueError(f"unknown proxy {proxy!r}; use auto, native or netcat")


def _start_ssh(target: ConnectionTarget) -> Stream:
    """Start ``ssh`` and wrap its pipes.

    :param target: a target with the ``ssh`` transport.
    :returns: the stream.
    :raises ConnectionError: if the ssh program cannot be started.
    """
    try:
        process = subprocess.Popen(
            ssh_command(target), stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
    except OSError as error:
        raise ConnectionError(f"cannot start ssh: {error}") from error
    return ProcessStream(process)


def _connect_tcp(target: ConnectionTarget) -> Stream:
    """Connect to a TCP port, with TLS if the transport asks for it.

    :param target: a target with the ``tls`` or ``tcp`` transport.
    :returns: the stream.
    :raises ConnectionError: if the host cannot be reached.
    :raises ProtocolError: if a TLS server does not accept our certificate.
    """
    try:
        connection = socket.create_connection(
            (str(target.host), int(target.port or 0)), CONNECT_TIMEOUT_SECONDS
        )
    except OSError as error:
        raise ConnectionError(
            f"cannot reach {target.host}:{target.port}: {error}"
        ) from error

    connection.settimeout(None)
    if target.transport != "tls":
        return SocketStream(connection)
    return _tls_stream(target, connection)


def _tls_stream(target: ConnectionTarget, connection: socket.socket) -> Stream:
    """Do the TLS handshake and the libvirt acceptance byte.

    :param target: a target with the ``tls`` transport.
    :param connection: the connected TCP socket.
    :returns: the stream over TLS.
    :raises ConnectionError: if the handshake fails.
    :raises ProtocolError: if the server does not accept our certificate.
    """
    secure: ssl.SSLSocket | None = None
    try:
        secure = tls_context(target).wrap_socket(
            connection, server_hostname=target.host
        )
        accepted = secure.recv(1)
    except (ssl.SSLError, OSError) as error:
        (secure or connection).close()
        raise ConnectionError(f"TLS to {target.host} failed: {error}") from error

    if accepted != TLS_ACCEPTED:
        secure.close()
        raise ProtocolError("the server did not accept our client certificate")
    return SocketStream(secure)
