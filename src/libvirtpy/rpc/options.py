"""Settings of a connection: call timeout and keepalive."""

from dataclasses import dataclass

__all__ = ["MAX_RECONNECT_DELAY", "ConnectionOptions"]

MAX_RECONNECT_DELAY = 30.0


@dataclass(frozen=True)
class ConnectionOptions:
    """How a connection watches the daemon.

    The keepalive works like libvirt's: after ``keepalive_interval`` seconds without
    anything received the client sends a ping, and it gives the connection up after
    ``keepalive_count`` unanswered pings. A daemon that hangs or a network that
    drops silently is therefore noticed in about
    ``keepalive_interval * (keepalive_count + 1)`` seconds, and every waiting call
    fails with ``ConnectionLostError``.
    """

    call_timeout: float | None = None
    """Seconds a call may wait for its reply; ``None`` waits as long as it takes
    (a volume wipe or a big upload can be slow). A call that times out raises
    ``CallTimeoutError`` and the connection stays usable."""
    keepalive_interval: float | None = 5.0
    """Seconds of silence before a ping; ``None`` turns the keepalive off."""
    keepalive_count: int = 5
    """Unanswered pings after which the daemon is considered dead."""
    reconnect_attempts: int = 0
    """How many times a lost connection is opened again before giving up; ``0``
    never reconnects (the next call fails with ``ConnectionLostError``)."""
    reconnect_delay: float = 1.0
    """Seconds before the second attempt; each further wait doubles, up to
    ``MAX_RECONNECT_DELAY``. The first attempt is made at once."""

    @property
    def reconnects(self) -> bool:
        """Tell whether a lost connection is opened again.

        :returns: ``True`` if ``reconnect_attempts`` is positive.
        """
        return self.reconnect_attempts > 0

    def reconnect_waits(self) -> list[float]:
        """List the waits before each reconnect attempt.

        :returns: one value per attempt: 0 for the first, then ``reconnect_delay``
            doubling, never more than ``MAX_RECONNECT_DELAY``.
        """
        waits = [0.0]
        delay = self.reconnect_delay
        for _ in range(self.reconnect_attempts - 1):
            waits.append(min(delay, MAX_RECONNECT_DELAY))
            delay *= 2
        return waits[: self.reconnect_attempts]

    @property
    def dead_after(self) -> float | None:
        """Seconds of silence after which the connection is given up.

        :returns: the limit, or ``None`` if the keepalive is off.
        """
        if self.keepalive_interval is None:
            return None
        return self.keepalive_interval * (self.keepalive_count + 1)
