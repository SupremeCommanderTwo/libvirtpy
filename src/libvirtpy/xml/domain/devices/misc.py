"""Small devices: ``<panic>``, ``<watchdog>`` and ``<rng>``.

See https://libvirt.org/formatdomain.html#events-configuration (panic),
https://libvirt.org/formatdomain.html#watchdog-device and
https://libvirt.org/formatdomain.html#random-number-generator-device
"""

from typing import Literal

from pydantic import Field
from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OptionalText, ScaledInteger, YesNo
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.chardev import (
    CharDevLog,
    CharDevProtocol,
    CharDevSource,
    CharDevType,
)
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi, VirtioDriverOptions

__all__ = [
    "Crypto",
    "Lease",
    "Panic",
    "Pstore",
    "Rng",
    "RngBackend",
    "RngDriver",
    "RngRate",
    "Vsock",
    "Watchdog",
]


class Panic(LibvirtXmlModel, tag="panic"):
    """``<panic>``: a device that tells the host the guest has crashed."""

    model: Literal["isa", "pseries", "hyperv", "s390", "pvpanic"] | None = attr(
        name="model", default=None
    )
    alias: Alias | None = element(tag="alias", default=None)
    address: Address | None = element(tag="address", default=None)


class Watchdog(LibvirtXmlModel, tag="watchdog"):
    """``<watchdog>``: a guest watchdog timer."""

    model: Literal["i6300esb", "ib700", "diag288", "itco"] = attr(name="model")
    action: (
        Literal["reset", "shutdown", "poweroff", "pause", "none", "dump", "inject-nmi"]
        | None
    ) = attr(name="action", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)


class RngDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>`` of an RNG device: virtio options only."""


class RngRate(LibvirtXmlModel, tag="rate"):
    """``<rate>``: at most ``bytes`` bytes per ``period`` milliseconds."""

    bytes: int = attr(name="bytes", ge=1)
    period: int | None = attr(name="period", default=None, ge=1)


class RngBackend(LibvirtXmlModel, tag="backend"):
    """``<backend>``: where the random numbers come from.

    ``random`` has a device path as text, ``egd`` a character device
    ``type`` with ``<source>``, and ``builtin`` neither.
    """

    model: Literal["random", "egd", "builtin"] = attr(name="model")
    value: OptionalText = Field(
        default=None, description="Element text: the device path of ``random``."
    )
    type: CharDevType | None = attr(name="type", default=None, description="``egd``.")
    sources: list[CharDevSource] = element(tag="source", default_factory=list)
    protocol: CharDevProtocol | None = element(tag="protocol", default=None)
    log: CharDevLog | None = element(tag="log", default=None)


class Rng(LibvirtXmlModel, tag="rng"):
    """``<rng>``: a random number generator device."""

    model: Literal["virtio", "virtio-transitional", "virtio-non-transitional"] = attr(
        name="model"
    )
    driver: RngDriver | None = element(tag="driver", default=None)
    rate: RngRate | None = element(tag="rate", default=None)
    backend: RngBackend = element(tag="backend")
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)


class VsockCid(LibvirtXmlModel, tag="cid"):
    auto: YesNo | None = attr(name="auto", default=None)
    address: int | None = attr(name="address", default=None, ge=0)


class VsockDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>`` of a vsock device: virtio options only."""


class Vsock(LibvirtXmlModel, tag="vsock"):
    """``<vsock>``: a host/guest socket device."""

    model: (
        Literal["virtio", "virtio-transitional", "virtio-non-transitional"] | None
    ) = attr(name="model", default=None)
    cid: VsockCid | None = element(tag="cid", default=None)
    driver: VsockDriver | None = element(tag="driver", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)


class CryptoBackend(LibvirtXmlModel, tag="backend"):
    model: Literal["builtin", "lkcf"] = attr(name="model")
    queues: int | None = attr(name="queues", default=None, ge=1)


class CryptoDriver(VirtioDriverOptions, tag="driver"):
    """``<driver>`` of a crypto device: virtio options only."""


class Crypto(LibvirtXmlModel, tag="crypto"):
    """``<crypto>``: a virtio crypto device."""

    model: Literal["virtio"] = attr(name="model")
    type: Literal["qemu"] = attr(name="type")
    backend: CryptoBackend = element(tag="backend")
    driver: CryptoDriver | None = element(tag="driver", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    address: Address | None = element(tag="address", default=None)


class LeaseTarget(LibvirtXmlModel, tag="target"):
    path: str = attr(name="path")
    offset: int | None = attr(name="offset", default=None, ge=0)


class Lease(LibvirtXmlModel, tag="lease"):
    """``<lease>``: a lock manager lease."""

    lockspace: str = element(tag="lockspace")
    key: str = element(tag="key")
    target: LeaseTarget = element(tag="target")


class PstoreSize(ScaledInteger, tag="size"):
    """``<size>``: the size of the persistent store."""


class Pstore(LibvirtXmlModel, tag="pstore"):
    """``<pstore>``: a persistent store for guest crash data."""

    backend: Literal["acpi-erst"] = attr(name="backend")
    path: str | None = element(tag="path", default=None)
    size: PstoreSize = element(tag="size")
    alias: Alias | None = element(tag="alias", default=None)
    address: Address | None = element(tag="address", default=None)
