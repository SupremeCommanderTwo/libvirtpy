"""Understanding libvirt URIs: driver, transport, host and parameters."""

from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlparse

__all__ = ["HYPERVISOR_DAEMONS", "ConnectionTarget", "parse_uri"]

HYPERVISOR_DAEMONS = {
    "qemu": "virtqemud",
    "lxc": "virtlxcd",
    "xen": "virtxend",
    "vbox": "virtvboxd",
    "ch": "virtchd",
    "bhyve": "virtbhyved",
    "vz": "virtvzd",
}
DEFAULT_PORTS = {"tls": 16514, "tcp": 16509}
LOCAL_TRANSPORTS = ("", "unix")
REMOTE_TRANSPORTS = ("ssh", "tls", "tcp")


@dataclass(frozen=True)
class ConnectionTarget:
    """What a libvirt URI asks for."""

    uri: str
    driver: str
    """The hypervisor driver: ``qemu``, ``lxc``, ..."""
    session: bool
    """``True`` for ``.../session``: the daemon of the user, not of the system."""
    transport: str = ""
    """``""``/``unix`` for this machine, or ``ssh``, ``tls``, ``tcp``."""
    host: str | None = None
    port: int | None = None
    user: str | None = None
    parameters: dict[str, str] = field(default_factory=dict)
    """The query of the URI (``keyfile``, ``pkipath``, ``no_verify``, ...)."""

    @property
    def remote(self) -> bool:
        """Whether the daemon runs on another host."""
        return self.transport in REMOTE_TRANSPORTS

    @property
    def protected(self) -> bool:
        """Whether the channel is already private: not plain TCP."""
        return self.transport != "tcp"

    @property
    def open_name(self) -> str:
        """The URI the remote daemon is asked to open: no transport, host or query."""
        scope = "session" if self.session else "system"
        return f"{self.driver}:///{scope}"


def parse_uri(uri: str) -> ConnectionTarget:
    """Understand a libvirt URI such as ``qemu+ssh://user@host/system``.

    :param uri: the URI.
    :returns: the target.
    :raises NotImplementedError: for a transport other than unix, ssh, tls, tcp.
    :raises ValueError: if the driver is unknown or a remote URI has no host.
    """
    parsed = urlparse(uri)
    driver, _, transport = parsed.scheme.partition("+")

    if driver not in HYPERVISOR_DAEMONS:
        raise ValueError(f"unknown libvirt driver {driver!r} in {uri!r}")
    if transport not in (*LOCAL_TRANSPORTS, *REMOTE_TRANSPORTS):
        raise NotImplementedError(f"transport {transport!r} is not supported")
    if transport in REMOTE_TRANSPORTS and not parsed.hostname:
        raise ValueError(f"{uri!r} needs a host for the {transport} transport")
    if transport in LOCAL_TRANSPORTS and parsed.hostname:
        raise ValueError(f"{uri!r} names a host but no remote transport")

    return ConnectionTarget(
        uri=uri,
        driver=driver,
        session=parsed.path == "/session",
        transport=transport,
        host=parsed.hostname,
        port=parsed.port or DEFAULT_PORTS.get(transport),
        user=parsed.username,
        parameters=dict(parse_qsl(parsed.query)),
    )
