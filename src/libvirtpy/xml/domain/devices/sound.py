"""``<sound>``: sound cards. (Host audio backends are ``<audio>``.)

See https://libvirt.org/formatdomain.html#sound-devices
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi, VirtioDriverOptions
from libvirtpy.xml.domain.devices.graphics import GraphicsAudio

__all__ = ["Sound", "SoundCodec", "SoundDriver"]


class SoundCodec(LibvirtXmlModel, tag="codec"):
    """``<codec>``: an ICH6/ICH9 codec."""

    type: Literal["duplex", "micro", "output"] = attr(name="type")


class SoundDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>`` of a sound card: virtio options only."""


class Sound(LibvirtXmlModel, tag="sound"):
    """``<sound>``: a sound card."""

    model: Literal[
        "sb16", "es1370", "pcspk", "ac97", "ich6", "ich7", "ich9", "usb", "virtio"
    ] = attr(name="model")
    multichannel: YesNo | None = attr(name="multichannel", default=None)
    streams: int | None = attr(name="streams", default=None, ge=0)
    audio: GraphicsAudio | None = element(tag="audio", default=None)
    codecs: list[SoundCodec] = element(tag="codec", default_factory=list)
    driver: SoundDriver | None = element(tag="driver", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
