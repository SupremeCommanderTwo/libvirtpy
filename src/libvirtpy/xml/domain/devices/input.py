"""``<input>``: mice, tablets, keyboards and passed-through input devices.

One model per kind of ``type``; ``Input`` is their union (see
``libvirtpy.xml.domain.devices.address`` for why it is a plain union).

See https://libvirt.org/formatdomain.html#input-devices
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi, VirtioDriverOptions

__all__ = [
    "EvdevInput",
    "EvdevInputSource",
    "HidInput",
    "Input",
    "InputDriver",
    "PassthroughInput",
    "PassthroughInputSource",
]


class InputDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>`` of an input device: virtio options only."""


class _InputBase(LibvirtXmlModel, tag="input"):
    """Fields every input type has."""

    model: (
        Literal["virtio", "virtio-transitional", "virtio-non-transitional"] | None
    ) = attr(name="model", default=None)
    driver: InputDriver | None = element(tag="driver", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)


class HidInput(_InputBase, tag="input"):
    """``type='mouse'``, ``'tablet'`` or ``'keyboard'``: an emulated device."""

    type: Literal["tablet", "mouse", "keyboard"] = attr(name="type")
    bus: Literal["ps2", "usb", "xen", "virtio"] | None = attr(name="bus", default=None)


class PassthroughInputSource(LibvirtXmlModel, tag="source"):
    evdev: str = attr(name="evdev", description="Host event device path.")


class PassthroughInput(_InputBase, tag="input"):
    """``type='passthrough'``: a host event device via virtio. Since 1.3.0."""

    type: Literal["passthrough"] = attr(name="type")
    bus: Literal["virtio"] = attr(name="bus")
    source: PassthroughInputSource = element(tag="source")


class EvdevInputSource(LibvirtXmlModel, tag="source"):
    dev: str = attr(name="dev", description="Host event device path.")
    grab: Literal["all"] | None = attr(name="grab", default=None)
    grab_toggle: (
        Literal[
            "ctrl-ctrl",
            "alt-alt",
            "shift-shift",
            "meta-meta",
            "scrolllock",
            "ctrl-scrolllock",
        ]
        | None
    ) = attr(name="grabToggle", default=None)
    repeat: OnOff | None = attr(name="repeat", default=None)


class EvdevInput(_InputBase, tag="input"):
    """``type='evdev'``: a host event device shared with the guest. Since 7.4.0."""

    type: Literal["evdev"] = attr(name="type")
    source: EvdevInputSource = element(tag="source")


Input = HidInput | PassthroughInput | EvdevInput
"""Any ``<input>``; the variant is chosen by its ``type`` attribute."""
