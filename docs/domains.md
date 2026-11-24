# Managing domains

A domain is a virtual machine. Everything below runs on the fake daemon too (see
{doc}`testing`), so you can try it without libvirt; replace
`LibvirtClient(FakeLibvirt())` with `LibvirtClient.open("qemu:///system")` for a real
host.

## Build a domain from scratch

A {class}`~libvirtpy.xml.Domain` is a pydantic model: build it in Python, and nothing is
written as XML until you hand it to the client.

```python
from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.xml import Domain
from libvirtpy.xml.domain import Memory, Os, OsType, Vcpu
from libvirtpy.xml.domain.devices import Devices, DiskTarget, FileDisk, NetworkInterface
from libvirtpy.xml.domain.devices.disk import DiskDriver
from libvirtpy.xml.domain.devices.interface import NetworkSourceInfo
from libvirtpy.xml.domain.storage_source import FileSource

domain = Domain(
    type="kvm",
    name="web1",
    memory=Memory(value=1, unit="GiB"),
    vcpu=Vcpu(value=2),
    os=Os(type=OsType(value="hvm", arch="x86_64", machine="q35")),
    devices=Devices(
        disks=[
            FileDisk(
                device="disk",
                driver=DiskDriver(name="qemu", type="qcow2"),
                source=FileSource(file="/var/lib/libvirt/images/web1.qcow2"),
                target=DiskTarget(dev="vda", bus="virtio"),
            )
        ],
        interfaces=[
            NetworkInterface(
                type="network", source=NetworkSourceInfo(network="default")
            )
        ],
    ),
)

client = LibvirtClient(FakeLibvirt())
stored = client.define_domain(domain)  # persistent, not started
print(stored.name, stored.uuid)  # libvirt filled in the UUID
```

`define_domain` returns the configuration as the daemon keeps it. Use `create_domain`
instead to start a *transient* domain that disappears when it stops. Both also accept
XML text, if you already have it.

## Life cycle

```python
client.start_domain("web1")
print(client.get_domain_state("web1").name)  # RUNNING
print(client.get_domain_info("web1").vcpus)

client.suspend_domain("web1")
client.resume_domain("web1")
client.reboot_domain("web1")

client.shutdown_domain("web1")  # asks the guest to power off
# client.destroy_domain("web1")                  # or: pulls the plug
client.undefine_domain("web1")  # removes the configuration
```

`shutdown_domain` is polite and returns at once; `destroy_domain` stops the guest
immediately. A call that does not fit the state (shutting down a stopped domain) raises
{class}`~libvirtpy.rpc.errors.OperationInvalidError`.

## Read, edit, write back

```python
domain = client.lookup_domain("web1")
domain.vcpu.value = 4
domain.memory.value = 2
client.define_domain(domain)  # the change takes effect at next start
```

Because the model keeps every element it understands, an edit does not disturb the
rest of the document. `None` means "not set": libvirt's defaults are never filled in
by the library.

## Change a running domain

Most setters take the model's new value and return the updated domain:

```python
client.set_domain_vcpus("web1", 8)
client.set_domain_memory("web1", 2 * 1024 * 1024)  # KiB
client.set_domain_autostart("web1", True)
```

Hot-plug a device by passing its model:

```python
from libvirtpy.xml.domain.devices import DiskTarget, FileDisk
from libvirtpy.xml.domain.storage_source import FileSource

extra = FileDisk(
    device="disk",
    source=FileSource(file="/var/lib/libvirt/images/extra.qcow2"),
    target=DiskTarget(dev="vdb", bus="virtio"),
)
client.attach_domain_device("web1", extra)
client.detach_domain_device("web1", extra)
```

### Live or persistent: flags

On a real daemon many calls take `flags=` that say whether to change the running
guest, its stored configuration, or both. The value is an `int`, built from libvirt's
`VIR_DOMAIN_AFFECT_LIVE` (1) and `VIR_DOMAIN_AFFECT_CONFIG` (2); each method's docstring
names the libvirt enum it takes.

```python
LIVE, CONFIG = 1, 2
client.set_domain_vcpus("web1", 4, flags=LIVE | CONFIG)
```

## A glance at the screen and the console

These return streams ({doc}`events-streams`) and need a running guest on a real daemon:

```python
import shutil

with client.take_domain_screenshot("web1") as image, open("shot.png", "wb") as out:
    shutil.copyfileobj(image, out)
```

## Save and restore

`save_domain(domain, path)` writes the memory image to a file and stops the guest;
`save_domain_managed` lets the daemon choose where, and `has_domain_managed_save` and
`remove_domain_managed_save` manage it. `get_saved_domain_xml` reads the configuration
inside a save file.
