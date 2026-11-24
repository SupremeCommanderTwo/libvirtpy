"""Find a domain in every way, edit its model, and write it back."""

from common import make_domain

from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.xml.domain import Memory
from libvirtpy.xml.domain.devices import (
    DiskTarget,
    FileDisk,
)
from libvirtpy.xml.domain.storage_source import FileSource

client = LibvirtClient(FakeLibvirt())
defined = client.define_domain(make_domain("db1"))
client.start_domain("db1")

# The same domain, found by what you happen to have:
by_name = client.lookup_domain("db1")
by_uuid = client.lookup_domain(defined.uuid)  # text that looks like a UUID
by_id = client.lookup_domain(by_name.id)  # the runtime id, an int
by_model = client.lookup_domain(by_name)  # a model: its UUID is used
assert by_name.uuid == by_uuid.uuid == by_id.uuid == by_model.uuid
print("found by name, UUID, id and model:", by_name.name)

# The result is a plain model: edit it like any other and define it again.
client.shutdown_domain("db1")
domain = client.lookup_domain("db1")
domain.memory = Memory(value=4, unit="GiB")
assert domain.devices is not None
domain.devices.disks.append(
    FileDisk(
        device="disk",
        source=FileSource(file="/var/lib/libvirt/images/db1-data.qcow2"),
        target=DiskTarget(dev="vdb", bus="virtio"),
    )
)
client.define_domain(domain)

stored = client.lookup_domain("db1")
assert stored.devices is not None
print("memory:", stored.memory)
print("disks:", [disk.target.dev for disk in stored.devices.disks if disk.target])

# XML text works wherever a model does:
print(client.define_domain("<domain type='kvm'><name>raw1</name></domain>").uuid)
