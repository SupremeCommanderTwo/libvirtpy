# Quick start

Install (Python 3.14 or newer):

```sh
pip install libvirtpy
```

## Talk to a daemon

```python
from libvirtpy.client import LibvirtClient
from libvirtpy.xml import Domain

with LibvirtClient.open("qemu:///system") as client:
    for domain in client.list_domains():
        print(domain.name, domain.memory)

    vm = client.lookup_domain("vm")  # a Domain model, not a string
    client.set_domain_vcpus(vm, 4)  # a reference: id, name, UUID or model
    client.domain(vm).start()  # the same, as a proxy
```

`lookup_domain` returns a {class}`libvirtpy.xml.Domain`: memory, vCPUs, disks and
interfaces are attributes you can read and edit, and `define_domain` writes the
model back.

## The same, with `asyncio`

```python
import asyncio
from libvirtpy.client import AsyncLibvirtClient


async def main() -> None:
    async with await AsyncLibvirtClient.open("qemu:///system") as client:
        domains = await asyncio.gather(
            client.lookup_domain("a"), client.lookup_domain("b")
        )


asyncio.run(main())
```

`LibvirtClient` and `AsyncLibvirtClient` have the same methods; calls made at the
same time share one connection.

## No daemon at hand

`FakeLibvirt` is an in-memory daemon, so examples and your own tests run anywhere:

```python
from libvirtpy.client import FakeLibvirt, LibvirtClient

client = LibvirtClient(FakeLibvirt())
```

The `examples/` directory of the repository runs on it; `examples/real/` talks to a
real libvirt over a local socket, SSH or TLS.
