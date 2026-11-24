"""``<domain>``: the root element of a guest definition.

See https://libvirt.org/formatdomain.html#general-metadata
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.metadata import Metadata
from libvirtpy.xml._types import Uuid
from libvirtpy.xml.domain.blkiotune import Blkiotune, ThrottleGroups
from libvirtpy.xml.domain.clock import Clock
from libvirtpy.xml.domain.cpu import Cpu, Cputune, Vcpu, Vcpus
from libvirtpy.xml.domain.devices.devices import Devices
from libvirtpy.xml.domain.features import Features
from libvirtpy.xml.domain.iothread import DefaultIothread, IothreadIds
from libvirtpy.xml.domain.launch_security import LaunchSecurity
from libvirtpy.xml.domain.memory import (
    CurrentMemory,
    MaxMemory,
    Memory,
    MemoryBacking,
    MemTune,
)
from libvirtpy.xml.domain.misc import Idmap, Iommufd, Keywrap, Perf, Pm, Resource
from libvirtpy.xml.domain.namespaces import (
    BHYVE_NAMESPACE,
    LXC_NAMESPACE,
    VMWARE_NAMESPACE,
    XEN_NAMESPACE,
    BhyveCommandline,
    LxcNamespace,
    VmwareDatacenterPath,
    XenCommandline,
)
from libvirtpy.xml.domain.numa import NumaTune
from libvirtpy.xml.domain.os import Os
from libvirtpy.xml.domain.qemu import (
    QEMU_NAMESPACE,
    QemuCapabilities,
    QemuCommandline,
    QemuDeprecation,
    QemuOverride,
)
from libvirtpy.xml.domain.seclabel import Seclabel
from libvirtpy.xml.domain.sysinfo import Sysinfo

__all__ = ["CrashAction", "Domain", "LifecycleAction", "LockFailureAction"]

# https://libvirt.org/formatdomain.html#events-configuration
LifecycleAction = Literal["destroy", "restart", "preserve", "rename-restart"]
CrashAction = Literal[
    "destroy",
    "restart",
    "preserve",
    "rename-restart",
    "coredump-destroy",
    "coredump-restart",
    "preserve-running",
]
LockFailureAction = Literal["poweroff", "restart", "pause", "ignore"]


class Domain(LibvirtXmlModel, tag="domain"):
    """``<domain>``: a guest definition."""

    type: str = attr(
        name="type",
        description="Hypervisor driver, e.g. ``kvm``, ``qemu``, ``xen``, ``lxc``.",
    )
    id: int | None = attr(
        name="id", default=None, description="Runtime ID of a running guest."
    )
    name: str = element(tag="name")
    uuid: Uuid | None = element(tag="uuid", default=None)
    title: str | None = element(tag="title", default=None)
    description: str | None = element(tag="description", default=None)
    genid: Uuid | Literal[""] | None = element(
        tag="genid",
        default=None,
        description="VM generation ID; an empty ``<genid/>`` asks libvirt to make one.",
    )
    hwuuid: Uuid | None = element(tag="hwuuid", default=None)
    metadata: Metadata | None = element(tag="metadata", default=None)
    max_memory: MaxMemory | None = element(tag="maxMemory", default=None)
    memory: Memory | None = element(tag="memory", default=None)
    current_memory: CurrentMemory | None = element(tag="currentMemory", default=None)
    memtune: MemTune | None = element(tag="memtune", default=None)
    memory_backing: MemoryBacking | None = element(tag="memoryBacking", default=None)
    blkiotune: Blkiotune | None = element(tag="blkiotune", default=None)
    vcpu: Vcpu | None = element(tag="vcpu", default=None)
    vcpus: Vcpus | None = element(tag="vcpus", default=None)
    iothreads: int | None = element(tag="iothreads", default=None, ge=0)
    iothreadids: IothreadIds | None = element(tag="iothreadids", default=None)
    defaultiothread: DefaultIothread | None = element(
        tag="defaultiothread", default=None
    )
    cputune: Cputune | None = element(tag="cputune", default=None)
    numatune: NumaTune | None = element(tag="numatune", default=None)
    resource: Resource | None = element(tag="resource", default=None)
    bootloader: str | None = element(
        tag="bootloader",
        default=None,
        description="Host bootloader for paravirtualized guests. May be empty.",
    )
    bootloader_args: str | None = element(tag="bootloader_args", default=None)
    os: Os | None = element(tag="os", default=None)
    cpu: Cpu | None = element(tag="cpu", default=None)
    features: Features | None = element(tag="features", default=None)
    clock: Clock | None = element(tag="clock", default=None)
    on_poweroff: LifecycleAction | None = element(tag="on_poweroff", default=None)
    on_reboot: LifecycleAction | None = element(tag="on_reboot", default=None)
    on_crash: CrashAction | None = element(tag="on_crash", default=None)
    on_lockfailure: LockFailureAction | None = element(
        tag="on_lockfailure", default=None
    )
    pm: Pm | None = element(tag="pm", default=None)
    perf: Perf | None = element(tag="perf", default=None)
    keywrap: Keywrap | None = element(tag="keywrap", default=None)
    idmap: Idmap | None = element(tag="idmap", default=None)
    iommufd: Iommufd | None = element(tag="iommufd", default=None)
    throttlegroups: ThrottleGroups | None = element(tag="throttlegroups", default=None)
    devices: Devices | None = element(tag="devices", default=None)
    seclabels: list[Seclabel] = element(tag="seclabel", default_factory=list)
    sysinfos: list[Sysinfo] = element(tag="sysinfo", default_factory=list)
    launch_security: LaunchSecurity | None = element(tag="launchSecurity", default=None)

    # Extension namespaces of the drivers
    qemu_commandline: QemuCommandline | None = element(
        tag="commandline", ns="qemu", nsmap={"qemu": QEMU_NAMESPACE}, default=None
    )
    qemu_capabilities: QemuCapabilities | None = element(
        tag="capabilities", ns="qemu", nsmap={"qemu": QEMU_NAMESPACE}, default=None
    )
    qemu_deprecation: QemuDeprecation | None = element(
        tag="deprecation", ns="qemu", nsmap={"qemu": QEMU_NAMESPACE}, default=None
    )
    qemu_override: QemuOverride | None = element(
        tag="override", ns="qemu", nsmap={"qemu": QEMU_NAMESPACE}, default=None
    )
    vmware_datacenterpath: VmwareDatacenterPath | None = element(
        tag="datacenterpath",
        ns="vmware",
        nsmap={"vmware": VMWARE_NAMESPACE},
        default=None,
    )
    lxc_namespace: LxcNamespace | None = element(
        tag="namespace", ns="lxc", nsmap={"lxc": LXC_NAMESPACE}, default=None
    )
    xen_commandline: XenCommandline | None = element(
        tag="commandline", ns="xen", nsmap={"xen": XEN_NAMESPACE}, default=None
    )
    bhyve_commandline: BhyveCommandline | None = element(
        tag="commandline", ns="bhyve", nsmap={"bhyve": BHYVE_NAMESPACE}, default=None
    )
