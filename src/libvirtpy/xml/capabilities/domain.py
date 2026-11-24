"""``<domainCapabilities>``: what a hypervisor supports for a domain.

Read-only: libvirt generates it, you only parse it. Most of it is a list of
blocks that say whether a feature is ``supported`` and which values of it are
allowed (``<enum>``), so those share ``FeatureSupport``.

See https://libvirt.org/formatdomaincaps.html
"""

from typing import Literal, cast

from lxml import etree as lxml_etree
from pydantic_xml import attr, element, xml_field_serializer
from pydantic_xml.element.element import XmlElementWriter

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._xml_element import StableXmlElement

__all__ = [
    "CapsEnum",
    "DomainCapabilities",
    "FeatureSupport",
]

YesNo = Literal["yes", "no"]


class CapsEnum(LibvirtXmlModel, tag="enum"):
    """``<enum>``: the allowed values of an option."""

    name: str = attr(name="name")
    values: list[str] = element(tag="value", default_factory=list)


class FeatureSupport(LibvirtXmlModel):
    """Base of the blocks that say ``supported`` and list their ``<enum>``\\ s."""

    supported: YesNo = attr(name="supported")
    enums: list[CapsEnum] = element(tag="enum", default_factory=list)


class CapsVcpu(LibvirtXmlModel, tag="vcpu"):
    max: int = attr(name="max", ge=0)


class CapsIothreads(LibvirtXmlModel, tag="iothreads"):
    supported: YesNo = attr(name="supported")


class CapsFirmwareFeatures(FeatureSupport, tag="firmwareFeatures"):
    """``<firmwareFeatures>``: firmware features the hypervisor can select."""


class CapsLoader(LibvirtXmlModel, tag="loader"):
    """``<loader>``: the firmware images that can be used.

    Not a ``FeatureSupport``: the schema wants the ``<value>`` elements before
    the ``<enum>`` elements, and a base class's fields are written first.
    """

    supported: YesNo = attr(name="supported")
    values: list[str] = element(tag="value", default_factory=list)
    enums: list[CapsEnum] = element(tag="enum", default_factory=list)


class CapsVarstore(LibvirtXmlModel, tag="varstore"):
    supported: YesNo = attr(name="supported")


class CapsOs(FeatureSupport, tag="os"):
    """``<os>``: what ``<os>`` can be set to."""

    firmware_features: CapsFirmwareFeatures | None = element(
        tag="firmwareFeatures", default=None
    )
    loader: CapsLoader | None = element(tag="loader", default=None)
    varstore: CapsVarstore | None = element(tag="varstore", default=None)


class CapsCpuModel(LibvirtXmlModel, tag="model"):
    """``<model>`` of the ``host-model`` mode: the CPU the host would expose."""

    value: str = ""
    fallback: Literal["allow", "forbid"] | None = attr(name="fallback", default=None)
    vendor_id: str | None = attr(name="vendor_id", default=None)


class CapsCpuMaxPhysAddr(LibvirtXmlModel, tag="maxphysaddr"):
    mode: Literal["emulate", "passthrough"] = attr(name="mode")
    bits: int | None = attr(name="bits", default=None, ge=0)
    limit: int | None = attr(name="limit", default=None, ge=0)


class CapsCpuFeature(LibvirtXmlModel, tag="feature"):
    policy: Literal["force", "require", "optional", "disable", "forbid"] = attr(
        name="policy"
    )
    name: str = attr(name="name")


class HostPassthroughMode(FeatureSupport, tag="mode"):
    """``<mode name='host-passthrough'>``."""

    name: Literal["host-passthrough"] = attr(name="name")


class MaximumMode(FeatureSupport, tag="mode"):
    """``<mode name='maximum'>``."""

    name: Literal["maximum"] = attr(name="name")


class HostModelMode(LibvirtXmlModel, tag="mode"):
    """``<mode name='host-model'>``."""

    name: Literal["host-model"] = attr(name="name")
    supported: YesNo = attr(name="supported")
    model: CapsCpuModel | None = element(tag="model", default=None)
    vendor: str | None = element(tag="vendor", default=None)
    maxphysaddr: CapsCpuMaxPhysAddr | None = element(tag="maxphysaddr", default=None)
    features: list[CapsCpuFeature] = element(tag="feature", default_factory=list)


class CustomModel(LibvirtXmlModel, tag="model"):
    """``<model>`` of the ``custom`` mode: a CPU model the hypervisor knows."""

    value: str = ""
    usable: Literal["yes", "no", "unknown"] = attr(name="usable")
    deprecated: YesNo | None = attr(name="deprecated", default=None)
    canonical: str | None = attr(name="canonical", default=None)
    vendor: str = attr(name="vendor")


class BlockerFeature(LibvirtXmlModel, tag="feature"):
    name: str = attr(name="name")


class CustomBlockers(LibvirtXmlModel, tag="blockers"):
    """``<blockers>``: the host features that make a CPU model unusable."""

    model: str = attr(name="model")
    features: list[BlockerFeature] = element(tag="feature", default_factory=list)


class CustomMode(LibvirtXmlModel, tag="mode"):
    """``<mode name='custom'>``: the named CPU models.

    libvirt writes the ``<blockers>`` of an unusable model right after that
    model, and the schema requires it. ``models`` and ``blockers`` are two
    lists; they are written back interleaved, each ``<blockers model=X>``
    after the model ``X`` it explains.
    """

    name: Literal["custom"] = attr(name="name")
    supported: YesNo = attr(name="supported")
    models: list[CustomModel] = element(tag="model", default_factory=list)
    blockers: list[CustomBlockers] = element(tag="blockers", default_factory=list)

    @xml_field_serializer("models")
    def _write_models(
        self, element: XmlElementWriter, value: list[CustomModel], field_name: str
    ) -> XmlElementWriter:
        """Write each model, followed by the ``<blockers>`` that explain it.

        :param element: the ``<mode>`` element being written.
        :param value: the models to write.
        :param field_name: the field this writer serializes (``models``).
        :returns: ``element``, with the children appended.
        """
        for model in value:
            element.append_element(_as_element(model))
            for blockers in self.blockers:
                if blockers.model == model.value:
                    element.append_element(_as_element(blockers))
        return element

    @xml_field_serializer("blockers")
    def _write_unmatched_blockers(
        self, element: XmlElementWriter, value: list[CustomBlockers], field_name: str
    ) -> XmlElementWriter:
        """Write the ``<blockers>`` that name no model of this mode.

        :param element: the ``<mode>`` element being written.
        :param value: all the blockers of the mode.
        :param field_name: the field this writer serializes (``blockers``).
        :returns: ``element``, with the children appended.
        """
        model_names = {model.value for model in self.models}
        for blockers in value:
            if blockers.model not in model_names:
                element.append_element(_as_element(blockers))
        return element


CpuMode = HostPassthroughMode | MaximumMode | HostModelMode | CustomMode


"""Any ``<mode>`` of ``<cpu>``; the variant is chosen by its ``name`` attribute."""


class CapsCpu(LibvirtXmlModel, tag="cpu"):
    """``<cpu>``: the CPU modes the hypervisor supports."""

    modes: list[CpuMode] = element(tag="mode", default_factory=list)


class CapsMemoryBacking(FeatureSupport, tag="memoryBacking"):
    """``<memoryBacking>``: the memory backing options."""


class DiskCaps(FeatureSupport, tag="disk"):
    """``<disk>``: the disk options."""


class GraphicsCaps(FeatureSupport, tag="graphics"):
    """``<graphics>``: the graphics types."""


class VideoCaps(FeatureSupport, tag="video"):
    """``<video>``: the video models."""


class HostdevCaps(FeatureSupport, tag="hostdev"):
    """``<hostdev>``: the host device types."""


class RngCaps(FeatureSupport, tag="rng"):
    """``<rng>``: the RNG models and backends."""


class FilesystemCaps(FeatureSupport, tag="filesystem"):
    """``<filesystem>``: the filesystem drivers."""


class TpmCaps(FeatureSupport, tag="tpm"):
    """``<tpm>``: the TPM models and backends."""


class RedirdevCaps(FeatureSupport, tag="redirdev"):
    """``<redirdev>``: the redirection buses."""


class ChannelCaps(FeatureSupport, tag="channel"):
    """``<channel>``: the channel types."""


class CryptoCaps(FeatureSupport, tag="crypto"):
    """``<crypto>``: the crypto models."""


class InterfaceCaps(FeatureSupport, tag="interface"):
    """``<interface>``: the interface backends."""


class PanicCaps(FeatureSupport, tag="panic"):
    """``<panic>``: the panic models."""


class ConsoleCaps(FeatureSupport, tag="console"):
    """``<console>``: the console models."""


class CapsDevices(LibvirtXmlModel, tag="devices"):
    """``<devices>``: what each kind of device supports."""

    disk: DiskCaps | None = element(tag="disk", default=None)
    graphics: GraphicsCaps | None = element(tag="graphics", default=None)
    video: VideoCaps | None = element(tag="video", default=None)
    hostdev: HostdevCaps | None = element(tag="hostdev", default=None)
    rng: RngCaps | None = element(tag="rng", default=None)
    filesystem: FilesystemCaps | None = element(tag="filesystem", default=None)
    tpm: TpmCaps | None = element(tag="tpm", default=None)
    redirdev: RedirdevCaps | None = element(tag="redirdev", default=None)
    channel: ChannelCaps | None = element(tag="channel", default=None)
    crypto: CryptoCaps | None = element(tag="crypto", default=None)
    interface: InterfaceCaps | None = element(tag="interface", default=None)
    panic: PanicCaps | None = element(tag="panic", default=None)
    console: ConsoleCaps | None = element(tag="console", default=None)


class SupportOnly(LibvirtXmlModel):
    """Base of the features that only say whether they are supported."""

    supported: YesNo = attr(name="supported")


class GicCaps(FeatureSupport, tag="gic"):
    """``<gic>``: the interrupt controller versions."""


class VmcoreinfoCaps(SupportOnly, tag="vmcoreinfo"):
    """``<vmcoreinfo>``."""


class GenidCaps(SupportOnly, tag="genid"):
    """``<genid>``: VM generation ID."""


class BackingStoreInputCaps(SupportOnly, tag="backingStoreInput"):
    """``<backingStoreInput>``."""


class BackupCaps(SupportOnly, tag="backup"):
    """``<backup>``."""


class AsyncTeardownCaps(SupportOnly, tag="async-teardown"):
    """``<async-teardown>``."""


class S390PvCaps(SupportOnly, tag="s390-pv"):
    """``<s390-pv>``."""


class Ps2Caps(SupportOnly, tag="ps2"):
    """``<ps2>``."""


class TdxCaps(SupportOnly, tag="tdx"):
    """``<tdx>``."""


class SevCaps(SupportOnly, tag="sev"):
    """``<sev>``: AMD SEV parameters of the host."""

    cbitpos: int | None = element(tag="cbitpos", default=None, ge=0)
    reduced_phys_bits: int | None = element(tag="reducedPhysBits", default=None, ge=0)
    max_guests: int | None = element(tag="maxGuests", default=None, ge=0)
    max_es_guests: int | None = element(tag="maxESGuests", default=None, ge=0)
    cpu0_id: str | None = element(tag="cpu0Id", default=None)


class SgxSize(LibvirtXmlModel):
    """Base of ``<section_size>``: an amount in KiB."""

    value: int
    unit: Literal["KiB"] = attr(name="unit")


class SgxSectionSize(SgxSize, tag="section_size"):
    """``<section_size>``: the size of the EPC sections."""


class SgxSection(LibvirtXmlModel, tag="section"):
    node: int = attr(name="node", ge=0)
    size: int = attr(name="size", ge=0)
    unit: Literal["KiB"] = attr(name="unit")


class SgxSections(LibvirtXmlModel, tag="sections"):
    sections: list[SgxSection] = element(tag="section", default_factory=list)


class SgxCaps(SupportOnly, tag="sgx"):
    """``<sgx>``: Intel SGX parameters of the host."""

    flc: YesNo | None = element(tag="flc", default=None)
    sgx1: YesNo | None = element(tag="sgx1", default=None)
    sgx2: YesNo | None = element(tag="sgx2", default=None)
    section_size: SgxSectionSize | None = element(tag="section_size", default=None)
    sections: SgxSections | None = element(tag="sections", default=None)


class HypervDefaults(LibvirtXmlModel, tag="defaults"):
    spinlocks: int | None = element(tag="spinlocks", default=None, ge=0)
    stimer_direct: Literal["on", "off"] | None = element(
        tag="stimer_direct", default=None
    )
    tlbflush_direct: Literal["on", "off"] | None = element(
        tag="tlbflush_direct", default=None
    )
    tlbflush_extended: Literal["on", "off"] | None = element(
        tag="tlbflush_extended", default=None
    )
    vendor_id: str | None = element(tag="vendor_id", default=None)


class HypervCaps(FeatureSupport, tag="hyperv"):
    """``<hyperv>``: the supported enlightenments and their defaults."""

    defaults: HypervDefaults | None = element(tag="defaults", default=None)


class LaunchSecurityCaps(FeatureSupport, tag="launchSecurity"):
    """``<launchSecurity>``: the launch security types."""


class CapsFeatures(LibvirtXmlModel, tag="features"):
    """``<features>``: the domain features the hypervisor supports."""

    gic: GicCaps | None = element(tag="gic", default=None)
    vmcoreinfo: VmcoreinfoCaps | None = element(tag="vmcoreinfo", default=None)
    genid: GenidCaps | None = element(tag="genid", default=None)
    backing_store_input: BackingStoreInputCaps | None = element(
        tag="backingStoreInput", default=None
    )
    backup: BackupCaps | None = element(tag="backup", default=None)
    async_teardown: AsyncTeardownCaps | None = element(
        tag="async-teardown", default=None
    )
    s390_pv: S390PvCaps | None = element(tag="s390-pv", default=None)
    ps2: Ps2Caps | None = element(tag="ps2", default=None)
    tdx: TdxCaps | None = element(tag="tdx", default=None)
    sev: SevCaps | None = element(tag="sev", default=None)
    sgx: SgxCaps | None = element(tag="sgx", default=None)
    hyperv: HypervCaps | None = element(tag="hyperv", default=None)
    launch_security: LaunchSecurityCaps | None = element(
        tag="launchSecurity", default=None
    )


class DomainCapabilities(LibvirtXmlModel, tag="domainCapabilities"):
    """``<domainCapabilities>``: what a hypervisor supports for one domain type."""

    path: str | None = element(tag="path", default=None)
    domain: str = element(tag="domain")
    machine: str | None = element(tag="machine", default=None)
    arch: str = element(tag="arch")
    vcpu: CapsVcpu | None = element(tag="vcpu", default=None)
    iothreads: CapsIothreads | None = element(tag="iothreads", default=None)
    os: CapsOs | None = element(tag="os", default=None)
    cpu: CapsCpu | None = element(tag="cpu", default=None)
    memory_backing: CapsMemoryBacking | None = element(
        tag="memoryBacking", default=None
    )
    devices: CapsDevices | None = element(tag="devices", default=None)
    features: CapsFeatures | None = element(tag="features", default=None)


def _as_element(model: LibvirtXmlModel) -> StableXmlElement:
    """Return the XML of ``model`` as an element for a custom field serializer.

    :param model: the model to convert.
    :returns: its element, ready to append to the element being written.
    """
    return StableXmlElement.from_native(cast(lxml_etree._Element, model.to_xml_tree()))
