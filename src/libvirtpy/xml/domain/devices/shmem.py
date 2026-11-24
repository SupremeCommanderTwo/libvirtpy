"""``<shmem>``: shared memory between host and guest, or between guests.

See https://libvirt.org/formatdomain.html#shared-memory-device
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff, ScaledInteger
from libvirtpy.xml.domain.devices.address import Address
from libvirtpy.xml.domain.devices.common import Alias, DeviceAcpi

__all__ = ["Shmem", "ShmemMsi", "ShmemServer", "ShmemSize"]


class ShmemModel(LibvirtXmlModel, tag="model"):
    type: Literal["ivshmem", "ivshmem-plain", "ivshmem-doorbell"] = attr(name="type")


class ShmemSize(ScaledInteger, tag="size"):
    """``<size>``: the size of the shared memory region."""


class ShmemServer(LibvirtXmlModel, tag="server"):
    path: str | None = attr(name="path", default=None)


class ShmemMsi(LibvirtXmlModel, tag="msi"):
    ioeventfd: OnOff | None = attr(name="ioeventfd", default=None)
    vectors: int | None = attr(name="vectors", default=None, ge=0)


class Shmem(LibvirtXmlModel, tag="shmem"):
    """``<shmem>``: an inter-VM shared memory device."""

    name: str = attr(name="name", pattern=r"^[^/]*$")
    role: Literal["master", "peer"] | None = attr(name="role", default=None)
    model: ShmemModel | None = element(tag="model", default=None)
    size: ShmemSize | None = element(tag="size", default=None)
    server: ShmemServer | None = element(tag="server", default=None)
    msi: ShmemMsi | None = element(tag="msi", default=None)
    alias: Alias | None = element(tag="alias", default=None)
    acpi: DeviceAcpi | None = element(tag="acpi", default=None)
    address: Address | None = element(tag="address", default=None)
