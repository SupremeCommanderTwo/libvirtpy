# Snapshots, checkpoints and backups

## Snapshots

```python
from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.xml import Domain
from libvirtpy.xml.snapshot import Snapshot

client = LibvirtClient(FakeLibvirt())
client.define_domain(Domain(type="kvm", name="ci1"))
client.start_domain("ci1")

before = client.create_domain_snapshot(
    "ci1", Snapshot(name="before-upgrade", description="clean install")
)

for snapshot in client.list_domain_snapshots("ci1"):
    parent = snapshot.parent.name if snapshot.parent else None
    print(snapshot.name, snapshot.state, parent)

client.revert_domain_snapshot("ci1", "before-upgrade")  # back to that state
client.delete_domain_snapshot("ci1", "before-upgrade")
```

Snapshots form a tree: a snapshot's `parent` names the one it was taken on.
`get_domain_snapshot_parent`, `list_domain_snapshot_children` and
`get_current_domain_snapshot` walk it. On a real daemon, `flags=` selects the kind:
disk-only, external, quiesced through the guest agent, and so on (the flag enum is
named in each docstring).

## Checkpoints and backups

A *checkpoint* marks a point in time with a dirty-block bitmap per disk, so a later
*backup* can copy only what changed. Both documents are models
(`libvirtpy.xml.backup.Checkpoint` and `Backup`) or plain XML text, and both need a
running guest on a real daemon:

```python
checkpoint = (
    "<domaincheckpoint><name>c1</name><disks>"
    "<disk name='vda' checkpoint='bitmap'/></disks></domaincheckpoint>"
)
client.create_domain_checkpoint("vm", checkpoint)

backup = (
    "<domainbackup mode='pull'>"
    "<server transport='unix' socket='/run/libvirt/qemu/vm-backup.sock'/>"
    "<disks><disk name='vda' type='file'>"
    "<scratch file='/var/lib/libvirt/images/scratch.qcow2'/></disk></disks>"
    "</domainbackup>"
)
client.begin_domain_backup("vm", backup)
try:
    print(client.get_domain_backup("vm").mode)
    ...  # read the exported disks over NBD
finally:
    client.abort_domain_backup("vm")  # the job runs until it is aborted
```

In *pull* mode qemu serves the disks over NBD at the socket and your backup tool reads
them; the job stays until `abort_domain_backup`. Remove a checkpoint with
`delete_domain_checkpoint`; `list_domain_checkpoints`, `lookup_domain_checkpoint` and
`get_domain_checkpoint_parent` browse them.

```{note}
With SELinux enforcing, qemu may create sockets only in `/run/libvirt/qemu`, and files
root creates under `/var/tmp` cannot be deleted by an unprivileged user. Put backup
sockets and scratch files where qemu is allowed to write.
```
