"""``<launchSecurity>``: confidential guest launch (AMD SEV, Intel TDX, s390 PV).

One class per ``type``; ``LaunchSecurity`` is their plain union.

See https://libvirt.org/formatdomain.html#launch-security
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import YesNo

__all__ = [
    "LaunchSecurity",
    "S390PvLaunchSecurity",
    "SevLaunchSecurity",
    "SevSnpLaunchSecurity",
    "TdxLaunchSecurity",
    "TdxQuoteGenerationService",
]


class SevLaunchSecurity(LibvirtXmlModel, tag="launchSecurity"):
    """``type='sev'``: AMD SEV."""

    type: Literal["sev"] = attr(name="type")
    kernel_hashes: YesNo | None = attr(name="kernelHashes", default=None)
    cbitpos: int | None = element(tag="cbitpos", default=None, ge=0)
    reduced_phys_bits: int | None = element(tag="reducedPhysBits", default=None, ge=0)
    policy: str = element(tag="policy", description="Hex number, e.g. ``0x0003``.")
    handle: int | None = element(tag="handle", default=None, ge=0)
    dh_cert: str | None = element(tag="dhCert", default=None)
    session: str | None = element(tag="session", default=None)


class SevSnpLaunchSecurity(LibvirtXmlModel, tag="launchSecurity"):
    """``type='sev-snp'``: AMD SEV-SNP."""

    type: Literal["sev-snp"] = attr(name="type")
    kernel_hashes: YesNo | None = attr(name="kernelHashes", default=None)
    author_key: YesNo | None = attr(name="authorKey", default=None)
    vcek: YesNo | None = attr(name="vcek", default=None)
    cbitpos: int | None = element(tag="cbitpos", default=None, ge=0)
    reduced_phys_bits: int | None = element(tag="reducedPhysBits", default=None, ge=0)
    policy: str = element(tag="policy", description="Hex number, e.g. ``0x30000``.")
    guest_visible_workarounds: str | None = element(
        tag="guestVisibleWorkarounds", default=None
    )
    id_block: str | None = element(tag="idBlock", default=None)
    id_auth: str | None = element(tag="idAuth", default=None)
    host_data: str | None = element(tag="hostData", default=None)


class S390PvLaunchSecurity(LibvirtXmlModel, tag="launchSecurity"):
    """``type='s390-pv'``: s390 protected virtualization."""

    type: Literal["s390-pv"] = attr(name="type")


class TdxQuoteGenerationService(LibvirtXmlModel, tag="quoteGenerationService"):
    path: str | None = attr(name="path", default=None)


class TdxLaunchSecurity(LibvirtXmlModel, tag="launchSecurity"):
    """``type='tdx'``: Intel TDX."""

    type: Literal["tdx"] = attr(name="type")
    policy: str | None = element(tag="policy", default=None)
    mr_config_id: str | None = element(tag="mrConfigId", default=None)
    mr_owner: str | None = element(tag="mrOwner", default=None)
    mr_owner_config: str | None = element(tag="mrOwnerConfig", default=None)
    quote_generation_service: TdxQuoteGenerationService | None = element(
        tag="quoteGenerationService", default=None
    )


LaunchSecurity = (
    SevLaunchSecurity | SevSnpLaunchSecurity | S390PvLaunchSecurity | TdxLaunchSecurity
)
"""Any ``<launchSecurity>``; the variant is chosen by its ``type`` attribute."""
