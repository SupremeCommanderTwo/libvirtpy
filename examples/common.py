"""Sample models shared by the examples."""

from libvirtpy.xml import Domain
from libvirtpy.xml.domain import Memory, Os, OsType, Vcpu
from libvirtpy.xml.domain.devices import (
    Devices,
    DiskTarget,
    FileDisk,
    NetworkInterface,
)
from libvirtpy.xml.domain.devices.disk import DiskDriver
from libvirtpy.xml.domain.devices.interface import NetworkSourceInfo
from libvirtpy.xml.domain.storage_source import FileSource


def make_domain(name: str, *, vcpus: int = 2, memory_gib: int = 1) -> Domain:
    """Build a small KVM guest with one disk and one network interface.

    :param name: the domain name.
    :param vcpus: the number of virtual CPUs.
    :param memory_gib: the memory, in GiB.
    :returns: the domain model.
    """
    return Domain(
        type="kvm",
        name=name,
        memory=Memory(value=memory_gib, unit="GiB"),
        vcpu=Vcpu(value=vcpus),
        os=Os(type=OsType(value="hvm", arch="x86_64", machine="q35")),
        devices=Devices(
            disks=[
                FileDisk(
                    device="disk",
                    driver=DiskDriver(name="qemu", type="qcow2"),
                    source=FileSource(file=f"/var/lib/libvirt/images/{name}.qcow2"),
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
