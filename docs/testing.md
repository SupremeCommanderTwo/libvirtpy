# Testing your code

`FakeLibvirt` is an in-memory daemon that serves domains, networks, pools, volumes,
snapshots, secrets, filters, host interfaces and devices, storing them as the real
models. Other operations raise `NotSupportedError` on it.

```python
from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.xml import Domain

client = LibvirtClient(FakeLibvirt())
client.define_domain(Domain(type="kvm", name="vm"))
assert client.lookup_domain("vm").name == "vm"
```

`AsyncFakeTransport` does the same for `AsyncLibvirtClient`.
