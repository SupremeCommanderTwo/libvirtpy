"""An in-memory libvirt daemon, for examples and tests (a test double).

This package follows the exemptions of tests: ``tests/tools`` does not check its
docstrings or its layout.

``FakeLibvirt`` answers the same ``Request``s a real daemon would and keeps its
objects as the real XML models, so everything the clients return is what a
user would get: UUIDs are filled in, a started domain gets an ``id``, a pool
gets a target path, a volume gets a key.

It serves only the first operations of the client (domains, networks, pools,
volumes, snapshots, secrets, filters, interfaces, devices); the others answer
with ``NotSupportedError``. It is a test aid, not a simulator: it knows the
state rules that make the examples meaningful (you cannot start a running
domain) and nothing about a real hypervisor.

One module per area: ``_state`` (the objects and what all kinds share),
``_domains``, ``_storage``, ``_objects``; ``fake`` puts them together.
"""

from libvirtpy.client.testing.async_transport import AsyncFakeTransport
from libvirtpy.client.testing.fake import FakeLibvirt

__all__ = ["AsyncFakeTransport", "FakeLibvirt"]
