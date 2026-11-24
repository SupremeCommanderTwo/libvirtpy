"""``<video>``: graphics adapters.

``VideoModel`` is one model for all adapter types: they differ by one to
three optional attributes.

See https://libvirt.org/formatdomain.html#video-devices
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff, YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi, VirtioDriverOptions

__all__ = [
    "Video",
    "VideoAcceleration",
    "VideoDriver",
    "VideoModel",
    "VideoResolution",
]


class VideoAcceleration(LibvirtXmlModel, tag="acceleration"):
    accel3d: YesNo | None = attr(name="accel3d", default=None)
    accel2d: YesNo | None = attr(name="accel2d", default=None)
    rendernode: str | None = attr(
        name="rendernode", default=None, description="Host DRM render node."
    )


class VideoResolution(LibvirtXmlModel, tag="resolution"):
    """``<resolution>``: the minimum guest resolution. Since 5.9.0."""

    x: int = attr(name="x", ge=0)
    y: int = attr(name="y", ge=0)


class VideoModel(LibvirtXmlModel, tag="model"):
    """``<model>``: the emulated adapter and its memory."""

    type: Literal[
        "vga",
        "cirrus",
        "vmvga",
        "xen",
        "vbox",
        "gop",
        "none",
        "bochs",
        "ramfb",
        "qxl",
        "virtio",
    ] = attr(name="type")
    ram: int | None = attr(name="ram", default=None, ge=0, description="KiB, qxl.")
    vgamem: int | None = attr(
        name="vgamem", default=None, ge=0, description="KiB, qxl."
    )
    vram64: int | None = attr(
        name="vram64", default=None, ge=0, description="KiB, qxl."
    )
    device: (
        Literal[
            "virtio-vga",
            "virtio-vga-gl",
            "virtio-gpu",
            "virtio-gpu-gl",
            "vhost-user-vga",
            "vhost-user-gpu",
        ]
        | None
    ) = attr(name="device", default=None, description="Only for ``virtio``.")
    vram: int | None = attr(name="vram", default=None, ge=0, description="KiB.")
    heads: int | None = attr(name="heads", default=None, ge=0)
    primary: YesNo | None = attr(name="primary", default=None)
    blob: OnOff | None = attr(name="blob", default=None)
    edid: OnOff | None = attr(name="edid", default=None)
    acceleration: VideoAcceleration | None = element(tag="acceleration", default=None)
    resolution: VideoResolution | None = element(tag="resolution", default=None)


class VideoDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>`` of a video device."""

    name: Literal["qemu", "vhostuser"] | None = attr(name="name", default=None)
    vgaconf: Literal["io", "on", "off"] | None = attr(
        name="vgaconf", default=None, description="bhyve only."
    )


class Video(LibvirtXmlModel, tag="video"):
    """``<video>``: a graphics adapter."""

    driver: VideoDriver | None = element(tag="driver", default=None)
    model: VideoModel | None = element(tag="model", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
