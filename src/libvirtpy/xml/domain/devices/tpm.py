"""``<tpm>``: a virtual Trusted Platform Module.

One class per backend ``type`` (``passthrough``, ``emulator``, ``external``).

See https://libvirt.org/formatdomain.html#tpm-device
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import PresenceFlag, Uuid, YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias

__all__ = [
    "EmulatorTpmBackend",
    "ExternalTpmBackend",
    "PassthroughTpmBackend",
    "Tpm",
    "TpmBackend",
]


class TpmDevice(LibvirtXmlModel, tag="device"):
    path: str | None = attr(name="path", default=None)


class PassthroughTpmBackend(LibvirtXmlModel, tag="backend"):
    """``type='passthrough'``: a host TPM device."""

    type: Literal["passthrough"] = attr(name="type")
    version: Literal["1.2", "2.0"] | None = attr(name="version", default=None)
    device: TpmDevice | None = element(tag="device", default=None)


class TpmEncryption(LibvirtXmlModel, tag="encryption"):
    secret: Uuid = attr(name="secret")


class ActivePcrBanks(LibvirtXmlModel, tag="active_pcr_banks"):
    sha1: PresenceFlag | None = element(tag="sha1", default=None)
    sha256: PresenceFlag | None = element(tag="sha256", default=None)
    sha384: PresenceFlag | None = element(tag="sha384", default=None)
    sha512: PresenceFlag | None = element(tag="sha512", default=None)


class EmulatorSource(LibvirtXmlModel, tag="source"):
    type: Literal["file", "dir"] = attr(name="type")
    path: str = attr(name="path")


class TpmProfile(LibvirtXmlModel, tag="profile"):
    source: str | None = attr(name="source", default=None)
    remove_disabled: Literal["check", "fips-host"] | None = attr(
        name="removeDisabled", default=None
    )
    name: str | None = attr(name="name", default=None)


class EmulatorTpmBackend(LibvirtXmlModel, tag="backend"):
    """``type='emulator'``: swtpm."""

    type: Literal["emulator"] = attr(name="type")
    version: Literal["1.2", "2.0"] | None = attr(name="version", default=None)
    persistent_state: YesNo | None = attr(name="persistent_state", default=None)
    debug: int | None = attr(name="debug", default=None, ge=0, le=255)
    encryption: TpmEncryption | None = element(tag="encryption", default=None)
    active_pcr_banks: ActivePcrBanks | None = element(
        tag="active_pcr_banks", default=None
    )
    source: EmulatorSource | None = element(tag="source", default=None)
    profile: TpmProfile | None = element(tag="profile", default=None)


class ExternalSource(LibvirtXmlModel, tag="source"):
    type: Literal["unix"] = attr(name="type")
    path: str = attr(name="path")
    mode: Literal["connect"] = attr(name="mode")


class ExternalTpmBackend(LibvirtXmlModel, tag="backend"):
    """``type='external'``: a TPM emulator served on a socket."""

    type: Literal["external"] = attr(name="type")
    version: Literal["1.2", "2.0"] | None = attr(name="version", default=None)
    source: ExternalSource | None = element(tag="source", default=None)


TpmBackend = PassthroughTpmBackend | EmulatorTpmBackend | ExternalTpmBackend
"""Any TPM ``<backend>``; the variant is chosen by its ``type`` attribute."""


class Tpm(LibvirtXmlModel, tag="tpm"):
    """``<tpm>``: a TPM device."""

    model: Literal["tpm-tis", "tpm-crb", "tpm-spapr", "spapr-tpm-proxy"] | None = attr(
        name="model", default=None
    )
    backend: TpmBackend = element(tag="backend")
    alias: Alias | None = element(tag="alias", default=None)
    address: Address | None = element(tag="address", default=None)
