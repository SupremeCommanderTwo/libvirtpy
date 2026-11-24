"""A client of a libvirt daemon that speaks in ``libvirtpy.xml`` models.

``LibvirtClient.open(uri)`` talks to libvirt daemons in pure Python, no libvirt
library: ``qemu:///system`` over the UNIX sockets of this machine, or a remote
host with ``qemu+ssh://user@host/system``, ``qemu+tls://host/system`` or
``qemu+tcp://host/system``. SASL (``sasl=SaslCredentials(user, password)``) works
with SCRAM, DIGEST-MD5 and PLAIN on TLS, SSH and UNIX sockets. ``client.events()``
receives what the daemon pushes; ``open_domain_console``, ``take_domain_screenshot``
and ``upload_pool_volume``/``download_pool_volume`` return file-like streams.
``FakeLibvirt`` is an in-memory daemon for tests and examples.

``LibvirtClient`` (blocking) and ``AsyncLibvirtClient`` (``async``/``await``)
offer the same methods. They take references (an id, a name, a UUID or a
model) and return models::

    client = LibvirtClient.open("qemu:///system")
    domain = client.define_domain(Domain(type="kvm", name="vm"))
    client.set_domain_vcpus(domain, 4)           # or client.domain(domain).set_vcpus(4)
    print(client.lookup_domain("vm").vcpu)
"""

from libvirtpy.client.aio import AsyncLibvirtClient
from libvirtpy.client.client import LibvirtClient
from libvirtpy.client.testing import AsyncFakeTransport, FakeLibvirt
from libvirtpy.client.types import DomainInfo, DomainState
from libvirtpy.rpc.errors import LibvirtError
from libvirtpy.rpc.events import (
    DomainEventKind,
    DomainLifecycle,
    Event,
    NetworkEventKind,
    NodeDeviceEventKind,
    PoolEventKind,
    SecretEventKind,
)
from libvirtpy.rpc.sasl import SaslCredentials

__all__ = [
    "AsyncFakeTransport",
    "AsyncLibvirtClient",
    "DomainEventKind",
    "DomainInfo",
    "DomainLifecycle",
    "DomainState",
    "Event",
    "FakeLibvirt",
    "LibvirtClient",
    "LibvirtError",
    "NetworkEventKind",
    "NodeDeviceEventKind",
    "PoolEventKind",
    "SaslCredentials",
    "SecretEventKind",
]
