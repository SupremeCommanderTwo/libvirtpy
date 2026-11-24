"""A fake libvirt daemon listening on a local TCP port, optionally with TLS."""

import contextlib
import socket
import ssl
import threading

from tests.helpers.fake_rpc_server import FakeRpcServer

__all__ = ["RunningServer"]


class RunningServer:
    """A fake daemon listening on a local TCP port, optionally with TLS."""

    def __init__(
        self,
        context: ssl.SSLContext | None,
        sasl: tuple[str, str, str] | None = None,
    ) -> None:
        """Start listening.

        :param context: server-side TLS settings, or ``None`` for plain TCP.
        :param sasl: ``(mechanism, user, password)`` to demand SASL.
        """
        self.context = context
        self.daemon = FakeRpcServer(sasl)
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.port = self.listener.getsockname()[1]
        self.connections: list[socket.socket] = []
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()

    def close(self) -> None:
        """Stop listening: new connections are refused."""
        with contextlib.suppress(OSError):
            self.listener.shutdown(socket.SHUT_RDWR)  # wakes the blocked accept()
        self.listener.close()

    def drop_connections(self) -> None:
        """Cut every open connection, as a crash or a network failure would."""
        for connection in list(self.connections):
            with contextlib.suppress(OSError):
                connection.shutdown(socket.SHUT_RDWR)
            connection.close()
        self.connections.clear()

    def _accept_loop(self) -> None:
        while True:
            try:
                connection, _ = self.listener.accept()
            except OSError:
                return
            threading.Thread(
                target=self._serve, args=(connection,), daemon=True
            ).start()

    def _serve(self, connection: socket.socket) -> None:
        self.connections.append(connection)
        try:
            if self.context is not None:
                connection = self.context.wrap_socket(connection, server_side=True)
                connection.sendall(b"\x01")
            self.daemon.serve(lambda: connection.recv(65536), connection.sendall)
        except OSError, ssl.SSLError:
            pass
        finally:
            connection.close()
