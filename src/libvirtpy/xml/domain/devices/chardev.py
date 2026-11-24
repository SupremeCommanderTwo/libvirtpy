"""Character devices: ``<serial>``, ``<console>``, ``<parallel>``, ``<channel>``.

They share one structure: a ``type`` (how the host side is backed), one or
more ``<source>`` elements, an optional ``<protocol>``, ``<log>`` and a
``<target>``. The attributes a ``<source>`` uses depend on the ``type`` (``path``
for ``file``, ``host`` and ``service`` for ``tcp``, ...), but they are all
optional text attributes of one element, so ``CharDevSource`` is one model
(libvirt validates the combination). ``Rng`` reuses the same pieces.

See https://libvirt.org/formatdomain.html#consoles-serial-parallel-channel-devices
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff, YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi
from libvirtpy.xml.domain.devices.graphics import SpiceClipboard, SpiceMouse
from libvirtpy.xml.domain.storage_source import DeviceSeclabel, Reconnect

__all__ = [
    "Channel",
    "ChannelTarget",
    "CharDevLog",
    "CharDevProtocol",
    "CharDevSource",
    "CharDevTarget",
    "CharDevTargetModel",
    "CharDevType",
    "Console",
    "Parallel",
    "Serial",
]

CharDevType = Literal[
    "dev",
    "file",
    "pipe",
    "unix",
    "tcp",
    "udp",
    "null",
    "stdio",
    "vc",
    "pty",
    "spicevmc",
    "spiceport",
    "nmdm",
    "qemu-vdagent",
    "dbus",
]


class CharDevSource(LibvirtXmlModel, tag="source"):
    """``<source>``: the host side of a character device."""

    mode: str | None = attr(
        name="mode", default=None, description="``bind``/``connect`` for sockets."
    )
    path: str | None = attr(name="path", default=None)
    host: str | None = attr(name="host", default=None)
    service: str | None = attr(name="service", default=None)
    channel: str | None = attr(name="channel", default=None)
    master: str | None = attr(name="master", default=None)
    slave: str | None = attr(name="slave", default=None)
    append: OnOff | None = attr(name="append", default=None)
    tls: YesNo | None = attr(name="tls", default=None)
    reconnect: Reconnect | None = element(tag="reconnect", default=None)
    seclabels: list[DeviceSeclabel] = element(tag="seclabel", default_factory=list)
    clipboard: SpiceClipboard | None = element(tag="clipboard", default=None)
    mouse: SpiceMouse | None = element(tag="mouse", default=None)


class CharDevProtocol(LibvirtXmlModel, tag="protocol"):
    """``<protocol>``: the wire protocol of a ``tcp`` device."""

    type: Literal["raw", "telnet", "telnets", "tls"] | None = attr(
        name="type", default=None
    )


class CharDevLog(LibvirtXmlModel, tag="log"):
    """``<log>``: a file that records the device's output."""

    file: str = attr(name="file")
    append: OnOff | None = attr(name="append", default=None)


class CharDevTargetModel(LibvirtXmlModel, tag="model"):
    """``<model>`` of a serial target: the emulated UART."""

    name: Literal[
        "isa-serial",
        "usb-serial",
        "pci-serial",
        "spapr-vty",
        "pl011",
        "16550a",
        "sclpconsole",
        "sclplmconsole",
        "isa-debugcon",
    ] = attr(name="name")


class CharDevTarget(LibvirtXmlModel, tag="target"):
    """``<target>`` of a ``<serial>``, ``<console>`` or ``<parallel>``.

    ``type`` takes console values (``serial``, ``virtio``, ``xen``, ...) for a
    ``<console>`` and serial values (``isa-serial``, ...) for a ``<serial>``.
    """

    type: (
        Literal[
            "xen",
            "serial",
            "uml",
            "virtio",
            "lxc",
            "openvz",
            "sclp",
            "sclplm",
            "isa-serial",
            "usb-serial",
            "pci-serial",
            "spapr-vio-serial",
            "system-serial",
            "sclp-serial",
            "isa-debug",
        ]
        | None
    ) = attr(name="type", default=None)
    port: str | None = attr(name="port", default=None)
    model: CharDevTargetModel | None = element(tag="model", default=None)


class ChannelTarget(LibvirtXmlModel, tag="target"):
    """``<target>`` of a ``<channel>``: ``guestfwd``, ``virtio`` or ``xen``."""

    type: Literal["guestfwd", "virtio", "xen"] | None = attr(name="type", default=None)
    address: str | None = attr(
        name="address", default=None, description="``guestfwd`` only."
    )
    port: str | None = attr(name="port", default=None, description="``guestfwd``.")
    name: str | None = attr(name="name", default=None, description="virtio and xen.")
    state: Literal["connected", "disconnected"] | None = attr(
        name="state", default=None
    )


class _CharDevBase(LibvirtXmlModel):
    """Fields of every character device."""

    type: CharDevType = attr(name="type")
    sources: list[CharDevSource] = element(tag="source", default_factory=list)
    protocol: CharDevProtocol | None = element(tag="protocol", default=None)
    log: CharDevLog | None = element(tag="log", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    address: Address | None = element(tag="address", default=None)


class _PortBase(_CharDevBase):
    """Fields of the port-like devices (all but ``<channel>``)."""

    target: CharDevTarget | None = element(tag="target", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)


class Serial(_PortBase, tag="serial"):
    """``<serial>``: a serial port."""

    tty: str | None = attr(name="tty", default=None)


class Parallel(_PortBase, tag="parallel"):
    """``<parallel>``: a parallel port."""

    tty: str | None = attr(name="tty", default=None)


class Console(_PortBase, tag="console"):
    """``<console>``: a guest console."""

    type: CharDevType | None = attr(  # type: ignore[assignment]  # optional with tty
        name="type", default=None
    )
    tty: str | None = attr(
        name="tty", default=None, description="Host pty of an LXC console."
    )


class Channel(_CharDevBase, tag="channel"):
    """``<channel>``: a private host/guest communication channel."""

    target: ChannelTarget | None = element(tag="target", default=None)
