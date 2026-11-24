"""``<features>``: hypervisor features (``<clock>`` will follow).

See https://libvirt.org/formatdomain.html#hypervisor-features
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff, PresenceFlag, ScaledInteger, YesNo

__all__ = [
    "Aia",
    "Apic",
    "AsyncTeardown",
    "Capabilities",
    "Cfpc",
    "DirtyRing",
    "FeatureState",
    "Features",
    "Gic",
    "Hpt",
    "Hyperv",
    "Ibs",
    "Ioapic",
    "KvmFeatures",
    "Msrs",
    "Sbbc",
    "Smm",
    "SmmTseg",
    "Spinlocks",
    "Stimer",
    "Tcg",
    "Tlbflush",
    "VendorId",
    "XenFeatures",
    "XenPassthrough",
]


class FeatureState(LibvirtXmlModel):
    """A feature element with an optional ``state`` attribute, like ``<pmu/>``.

    The element tag comes from the field that uses it. An absent ``state``
    stays ``None``; libvirt treats the bare element as ``state='on'``.
    """

    state: OnOff | None = attr(name="state", default=None)


class Spinlocks(FeatureState):
    """``<spinlocks>`` of ``<hyperv>``: how often to retry before notifying."""

    retries: int | None = attr(name="retries", default=None, ge=0)


class Stimer(FeatureState):
    """``<stimer>`` of ``<hyperv>``."""

    direct: FeatureState | None = element(tag="direct", default=None)


class Tlbflush(FeatureState):
    """``<tlbflush>`` of ``<hyperv>``."""

    direct: FeatureState | None = element(tag="direct", default=None)
    extended: FeatureState | None = element(tag="extended", default=None)


class VendorId(FeatureState):
    """``<vendor_id>`` of ``<hyperv>``: the hypervisor vendor string."""

    value: str | None = attr(name="value", default=None, pattern=r"^[^,]{0,12}$")


class Hyperv(LibvirtXmlModel, tag="hyperv"):
    """``<hyperv>``: Hyper-V enlightenments for Windows guests."""

    mode: Literal["custom", "host-model", "passthrough"] | None = attr(
        name="mode", default=None
    )
    relaxed: FeatureState | None = element(tag="relaxed", default=None)
    vapic: FeatureState | None = element(tag="vapic", default=None)
    spinlocks: Spinlocks | None = element(tag="spinlocks", default=None)
    vpindex: FeatureState | None = element(tag="vpindex", default=None)
    runtime: FeatureState | None = element(tag="runtime", default=None)
    synic: FeatureState | None = element(tag="synic", default=None)
    stimer: Stimer | None = element(tag="stimer", default=None)
    reset: FeatureState | None = element(tag="reset", default=None)
    vendor_id: VendorId | None = element(tag="vendor_id", default=None)
    frequencies: FeatureState | None = element(tag="frequencies", default=None)
    reenlightenment: FeatureState | None = element(tag="reenlightenment", default=None)
    tlbflush: Tlbflush | None = element(tag="tlbflush", default=None)
    ipi: FeatureState | None = element(tag="ipi", default=None)
    evmcs: FeatureState | None = element(tag="evmcs", default=None)
    avic: FeatureState | None = element(tag="avic", default=None)
    emsr_bitmap: FeatureState | None = element(tag="emsr_bitmap", default=None)
    xmm_input: FeatureState | None = element(tag="xmm_input", default=None)


class DirtyRing(FeatureState):
    """``<dirty-ring>`` of ``<kvm>``."""

    size: int | None = attr(name="size", default=None, ge=0)


class KvmFeatures(LibvirtXmlModel, tag="kvm"):
    """``<kvm>``: KVM specific features."""

    hidden: FeatureState | None = element(tag="hidden", default=None)
    hint_dedicated: FeatureState | None = element(tag="hint-dedicated", default=None)
    poll_control: FeatureState | None = element(tag="poll-control", default=None)
    pv_ipi: FeatureState | None = element(tag="pv-ipi", default=None)
    dirty_ring: DirtyRing | None = element(tag="dirty-ring", default=None)


class XenPassthrough(FeatureState):
    """``<passthrough>`` of ``<xen>``."""

    mode: Literal["sync_pt", "share_pt"] | None = attr(name="mode", default=None)


class XenFeatures(LibvirtXmlModel, tag="xen"):
    """``<xen>``: Xen specific features."""

    e820_host: FeatureState | None = element(tag="e820_host", default=None)
    passthrough: XenPassthrough | None = element(tag="passthrough", default=None)


class Capabilities(LibvirtXmlModel, tag="capabilities"):
    """``<capabilities>``: Linux capabilities of an LXC container."""

    policy: Literal["default", "allow", "deny"] = attr(name="policy")
    audit_control: FeatureState | None = element(tag="audit_control", default=None)
    audit_write: FeatureState | None = element(tag="audit_write", default=None)
    block_suspend: FeatureState | None = element(tag="block_suspend", default=None)
    chown: FeatureState | None = element(tag="chown", default=None)
    dac_override: FeatureState | None = element(tag="dac_override", default=None)
    dac_read_search: FeatureState | None = element(tag="dac_read_search", default=None)
    fowner: FeatureState | None = element(tag="fowner", default=None)
    fsetid: FeatureState | None = element(tag="fsetid", default=None)
    ipc_lock: FeatureState | None = element(tag="ipc_lock", default=None)
    ipc_owner: FeatureState | None = element(tag="ipc_owner", default=None)
    kill: FeatureState | None = element(tag="kill", default=None)
    lease: FeatureState | None = element(tag="lease", default=None)
    linux_immutable: FeatureState | None = element(tag="linux_immutable", default=None)
    mac_admin: FeatureState | None = element(tag="mac_admin", default=None)
    mac_override: FeatureState | None = element(tag="mac_override", default=None)
    mknod: FeatureState | None = element(tag="mknod", default=None)
    net_admin: FeatureState | None = element(tag="net_admin", default=None)
    net_bind_service: FeatureState | None = element(
        tag="net_bind_service", default=None
    )
    net_broadcast: FeatureState | None = element(tag="net_broadcast", default=None)
    net_raw: FeatureState | None = element(tag="net_raw", default=None)
    setgid: FeatureState | None = element(tag="setgid", default=None)
    setfcap: FeatureState | None = element(tag="setfcap", default=None)
    setpcap: FeatureState | None = element(tag="setpcap", default=None)
    setuid: FeatureState | None = element(tag="setuid", default=None)
    sys_admin: FeatureState | None = element(tag="sys_admin", default=None)
    sys_boot: FeatureState | None = element(tag="sys_boot", default=None)
    sys_chroot: FeatureState | None = element(tag="sys_chroot", default=None)
    sys_module: FeatureState | None = element(tag="sys_module", default=None)
    sys_nice: FeatureState | None = element(tag="sys_nice", default=None)
    sys_pacct: FeatureState | None = element(tag="sys_pacct", default=None)
    sys_ptrace: FeatureState | None = element(tag="sys_ptrace", default=None)
    sys_rawio: FeatureState | None = element(tag="sys_rawio", default=None)
    sys_resource: FeatureState | None = element(tag="sys_resource", default=None)
    sys_time: FeatureState | None = element(tag="sys_time", default=None)
    sys_tty_config: FeatureState | None = element(tag="sys_tty_config", default=None)
    syslog: FeatureState | None = element(tag="syslog", default=None)
    wake_alarm: FeatureState | None = element(tag="wake_alarm", default=None)


class SmmTseg(ScaledInteger, tag="tseg"):
    """``<tseg>``: the size of the SMRAM."""


class Smm(FeatureState):
    """``<smm>``: System Management Mode; ``<tseg>`` is its SMRAM size."""

    tseg: SmmTseg | None = element(tag="tseg", default=None)


class HptMaxPageSize(ScaledInteger, tag="maxpagesize"):
    """``<maxpagesize>``: the largest page size of the hash page table."""


class Hpt(LibvirtXmlModel, tag="hpt"):
    """``<hpt>``: PowerPC hash page table settings."""

    resizing: Literal["enabled", "disabled", "required"] | None = attr(
        name="resizing", default=None
    )
    maxpagesize: HptMaxPageSize | None = element(tag="maxpagesize", default=None)


class Ioapic(LibvirtXmlModel, tag="ioapic"):
    """``<ioapic>``: which IOAPIC implementation to use."""

    driver: Literal["qemu", "kvm"] = attr(name="driver")


class Msrs(LibvirtXmlModel, tag="msrs"):
    """``<msrs>``: how the guest's access to unknown MSRs is handled."""

    unknown: Literal["ignore", "fault"] = attr(name="unknown")


class TbCache(ScaledInteger, tag="tb-cache"):
    """``<tb-cache>``: the size of the TCG translation block cache."""


class Tcg(LibvirtXmlModel, tag="tcg"):
    """``<tcg>``: software emulation settings."""

    tb_cache: TbCache | None = element(tag="tb-cache", default=None)


class AsyncTeardown(LibvirtXmlModel, tag="async-teardown"):
    enabled: YesNo | None = attr(name="enabled", default=None)


class Apic(LibvirtXmlModel, tag="apic"):
    """``<apic>``: use the programmable IRQ management."""

    eoi: OnOff | None = attr(
        name="eoi",
        default=None,
        description="Paravirtualized End of Interrupt. Since 0.10.2 (QEMU only).",
    )


class Gic(LibvirtXmlModel, tag="gic"):
    """``<gic>``: the ARM generic interrupt controller."""

    version: Literal["host", "2", "3"] | None = attr(name="version", default=None)


class Cfpc(LibvirtXmlModel, tag="cfpc"):
    """``<cfpc>``: cache flush on privilege change (PowerPC)."""

    value: Literal["broken", "workaround", "fixed"] = attr(name="value")


class Sbbc(LibvirtXmlModel, tag="sbbc"):
    """``<sbbc>``: speculation barrier bounds checking (PowerPC)."""

    value: Literal["broken", "workaround", "fixed"] = attr(name="value")


class Ibs(LibvirtXmlModel, tag="ibs"):
    """``<ibs>``: indirect branch speculation (PowerPC)."""

    value: Literal["broken", "workaround", "fixed-ibs", "fixed-ccd", "fixed-na"] = attr(
        name="value"
    )


class Aia(LibvirtXmlModel, tag="aia"):
    """``<aia>``: the RISC-V advanced interrupt architecture."""

    value: Literal["none", "aplic", "aplic-imsic"] = attr(name="value")


class Features(LibvirtXmlModel, tag="features"):
    """``<features>``: hypervisor features to turn on or off."""

    pae: PresenceFlag | None = element(tag="pae", default=None)
    acpi: PresenceFlag | None = element(tag="acpi", default=None)
    apic: Apic | None = element(tag="apic", default=None)
    hap: FeatureState | None = element(
        tag="hap", default=None, description="Hardware Assisted Paging."
    )
    viridian: PresenceFlag | None = element(tag="viridian", default=None)
    privnet: PresenceFlag | None = element(tag="privnet", default=None)
    pvspinlock: FeatureState | None = element(
        tag="pvspinlock", default=None, description="Paravirtual spinlocks."
    )
    pmu: FeatureState | None = element(
        tag="pmu",
        default=None,
        description="Performance monitoring unit. Since 1.2.12.",
    )
    hyperv: Hyperv | None = element(tag="hyperv", default=None)
    kvm: KvmFeatures | None = element(tag="kvm", default=None)
    xen: XenFeatures | None = element(tag="xen", default=None)
    capabilities: Capabilities | None = element(tag="capabilities", default=None)
    gic: Gic | None = element(tag="gic", default=None)
    smm: Smm | None = element(tag="smm", default=None)
    ioapic: Ioapic | None = element(tag="ioapic", default=None)
    hpt: Hpt | None = element(tag="hpt", default=None)
    vmcoreinfo: FeatureState | None = element(tag="vmcoreinfo", default=None)
    htm: FeatureState | None = element(tag="htm", default=None)
    nested_hv: FeatureState | None = element(tag="nested-hv", default=None)
    msrs: Msrs | None = element(tag="msrs", default=None)
    ccf_assist: FeatureState | None = element(tag="ccf-assist", default=None)
    cfpc: Cfpc | None = element(tag="cfpc", default=None)
    sbbc: Sbbc | None = element(tag="sbbc", default=None)
    ibs: Ibs | None = element(tag="ibs", default=None)
    tcg: Tcg | None = element(tag="tcg", default=None)
    async_teardown: AsyncTeardown | None = element(tag="async-teardown", default=None)
    ras: FeatureState | None = element(tag="ras", default=None)
    ps2: FeatureState | None = element(tag="ps2", default=None)
    aia: Aia | None = element(tag="aia", default=None)
    virtualization: PresenceFlag | None = element(tag="virtualization", default=None)
    vmport: FeatureState | None = element(
        tag="vmport",
        default=None,
        description="VMware IO port emulation. Since 1.2.16.",
    )
