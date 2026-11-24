"""USB-related devices: ``<hub>``, ``<redirdev>``, ``<redirfilter>``, ``<smartcard>``.

See https://libvirt.org/formatdomain.html#redirected-devices (and the sections
on USB hubs and smartcard devices).
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.chardev import (
    CharDevLog,
    CharDevProtocol,
    CharDevSource,
    CharDevTarget,
    CharDevType,
)
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi, DeviceBoot

__all__ = [
    "Hub",
    "RedirFilter",
    "Redirdev",
    "Smartcard",
    "UsbDeviceFilter",
]


class Hub(LibvirtXmlModel, tag="hub"):
    """``<hub>``: a USB hub."""

    type: Literal["usb"] = attr(name="type")
    alias: Alias | None = element(tag="alias", default=None)
    address: Address | None = element(tag="address", default=None)


class Redirdev(LibvirtXmlModel, tag="redirdev"):
    """``<redirdev>``: USB redirection from a client to the guest."""

    bus: Literal["usb"] = attr(name="bus")
    type: CharDevType = attr(name="type")
    sources: list[CharDevSource] = element(tag="source", default_factory=list)
    protocol: CharDevProtocol | None = element(tag="protocol", default=None)
    log: CharDevLog | None = element(tag="log", default=None)
    boot: DeviceBoot | None = element(tag="boot", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    address: Address | None = element(tag="address", default=None)


class UsbDeviceFilter(LibvirtXmlModel, tag="usbdev"):
    """``<usbdev>``: one rule of the redirection filter."""

    allow: YesNo = attr(name="allow")
    class_: str | None = attr(name="class", default=None)
    vendor: str | None = attr(name="vendor", default=None)
    product: str | None = attr(name="product", default=None)
    version: str | None = attr(name="version", default=None)


class RedirFilter(LibvirtXmlModel, tag="redirfilter"):
    """``<redirfilter>``: which USB devices may be redirected."""

    usbdevs: list[UsbDeviceFilter] = element(tag="usbdev", default_factory=list)


class Smartcard(LibvirtXmlModel, tag="smartcard"):
    """``<smartcard>``: a smartcard reader.

    ``mode`` is ``host``, ``host-certificates`` (with ``certificates`` and
    ``database``) or ``passthrough`` (a character device ``type``, with
    ``sources`` and ``target``).
    """

    mode: Literal["host", "host-certificates", "passthrough"] = attr(name="mode")
    type: CharDevType | None = attr(name="type", default=None)
    certificates: list[str] = element(tag="certificate", default_factory=list)
    database: str | None = element(tag="database", default=None)
    sources: list[CharDevSource] = element(tag="source", default_factory=list)
    protocol: CharDevProtocol | None = element(tag="protocol", default=None)
    log: CharDevLog | None = element(tag="log", default=None)
    target: CharDevTarget | None = element(tag="target", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
