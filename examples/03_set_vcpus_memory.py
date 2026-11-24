"""Change a domain while it exists: vCPUs, memory, autostart, devices."""

from common import make_domain

from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.xml.domain.devices import DiskTarget, FileDisk
from libvirtpy.xml.domain.storage_source import FileSource

client = LibvirtClient(FakeLibvirt())
client.define_domain(make_domain("app1", vcpus=2))
client.start_domain("app1")

# The operations return the updated model, so the change is visible at once.
domain = client.set_domain_vcpus("app1", 8)
print("vcpus:", domain.vcpu.value if domain.vcpu else None)

domain = client.set_domain_memory("app1", 2 * 1024 * 1024)  # KiB
print("current memory:", domain.current_memory)

client.set_domain_autostart("app1", True)
print("autostart:", client.get_domain_autostart("app1"))

# Hot-plug a disk: pass the device model.
extra = FileDisk(
    device="disk",
    source=FileSource(file="/var/lib/libvirt/images/extra.qcow2"),
    target=DiskTarget(dev="vdb", bus="virtio"),
)
client.attach_domain_device("app1", extra)
after_attach = client.lookup_domain("app1")
assert after_attach.devices is not None
print(
    "disks after attach:",
    [d.target.dev for d in after_attach.devices.disks if d.target],
)

client.detach_domain_device("app1", extra)
after_detach = client.lookup_domain("app1")
assert after_detach.devices is not None
print(
    "disks after detach:",
    [d.target.dev for d in after_detach.devices.disks if d.target],
)
