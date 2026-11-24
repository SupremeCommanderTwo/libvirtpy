"""The async face of the fake daemon."""

from libvirtpy.client.testing.fake import FakeLibvirt
from libvirtpy.client.transport import Request


class AsyncFakeTransport:
    """The async ``AsyncTransport`` of an ``AsyncLibvirtClient`` over a fake daemon."""

    def __init__(self, daemon: FakeLibvirt | None = None) -> None:
        """Create the transport.

        :param daemon: the daemon to serve from; a new empty one by default.
        """
        self.daemon = daemon if daemon is not None else FakeLibvirt()

    async def call(self, request: Request) -> object:
        """Serve one request, yielding to the event loop first like real I/O.

        :param request: the call to make.
        :returns: the reply.
        :raises LibvirtError: for the errors a real daemon would report.
        """
        import asyncio

        await asyncio.sleep(0)
        return self.daemon.call(request)

    async def close(self) -> None:
        """Close the connection (nothing to do for the fake)."""
