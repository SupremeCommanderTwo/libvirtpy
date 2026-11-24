"""Snapshots of a domain: create, list, revert, delete."""

from common import make_domain

from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.xml.snapshot import Snapshot

client = LibvirtClient(FakeLibvirt())
client.define_domain(make_domain("ci1"))
client.start_domain("ci1")

before = client.create_domain_snapshot(
    "ci1", Snapshot(name="before-upgrade", description="clean install")
)
print(f"created {before.name!r}: state {before.state}, parent {before.parent}")

client.shutdown_domain("ci1")
client.create_domain_snapshot("ci1", Snapshot(name="powered-off"))

for snapshot in client.list_domain_snapshots("ci1"):
    parent = snapshot.parent.name if snapshot.parent else None
    print(f"- {snapshot.name} ({snapshot.state}), parent: {parent}")

# Going back to a running snapshot starts the domain again.
client.revert_domain_snapshot("ci1", "before-upgrade")
print("after revert:", client.get_domain_state("ci1").name)

client.delete_domain_snapshot("ci1", "powered-off")
print("left:", [s.name for s in client.list_domain_snapshots("ci1")])
