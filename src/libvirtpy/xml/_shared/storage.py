"""Storage structures shared by ``<disk>`` sources, storage pools and volumes.

``domain`` and ``storage`` must not import each other, so the structures that
both use live here and each package re-exports them.
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import HexNumber, OnOff, ScaledInteger, Uuid, YesNo

__all__ = [
    "Allocation",
    "Capacity",
    "DeviceSeclabel",
    "HostPciAddress",
    "Permissions",
    "ScsiAdapter",
    "ScsiParentAddress",
    "StorageCipher",
    "StorageEncryption",
    "StorageIvgen",
    "StorageSecret",
    "Timestamps",
]


class Capacity(ScaledInteger, tag="capacity"):
    """``<capacity>``: the logical size."""


class Allocation(ScaledInteger, tag="allocation"):
    """``<allocation>``: the space actually used on the host."""


class StorageSecret(LibvirtXmlModel, tag="secret"):
    """``<secret>``: a libvirt secret, referenced by ``uuid`` or by ``usage``."""

    type: Literal["passphrase", "ceph", "iscsi"] = attr(name="type")
    uuid: Uuid | None = attr(name="uuid", default=None)
    usage: str | None = attr(name="usage", default=None)


class StorageCipher(LibvirtXmlModel, tag="cipher"):
    name: str = attr(name="name")
    size: int = attr(name="size", ge=0)
    mode: str | None = attr(name="mode", default=None)
    hash: str | None = attr(name="hash", default=None)


class StorageIvgen(LibvirtXmlModel, tag="ivgen"):
    name: str = attr(name="name")
    hash: str | None = attr(name="hash", default=None)


class StorageEncryption(LibvirtXmlModel, tag="encryption"):
    """``<encryption>``: how the volume is encrypted and where the key is."""

    format: Literal["default", "qcow", "luks", "luks2", "luks-any"] = attr(
        name="format"
    )
    engine: Literal["qemu", "librbd"] | None = attr(name="engine", default=None)
    secrets: list[StorageSecret] = element(tag="secret", default_factory=list)
    cipher: StorageCipher | None = element(tag="cipher", default=None)
    ivgen: StorageIvgen | None = element(tag="ivgen", default=None)


class HostPciAddress(LibvirtXmlModel, tag="address"):
    """``<address>`` of a host PCI device (no ``type`` attribute)."""

    domain: HexNumber | None = attr(name="domain", default=None)
    bus: HexNumber | None = attr(name="bus", default=None)
    slot: HexNumber | None = attr(name="slot", default=None)
    function: HexNumber | None = attr(name="function", default=None)
    multifunction: OnOff | None = attr(name="multifunction", default=None)


class ScsiParentAddress(LibvirtXmlModel, tag="parentaddr"):
    unique_id: int | None = attr(name="unique_id", default=None, ge=1)
    address: HostPciAddress | None = element(tag="address", default=None)


class ScsiAdapter(LibvirtXmlModel, tag="adapter"):
    """``<adapter>``: a SCSI host (``scsi_host``) or Fibre Channel host."""

    type: Literal["scsi_host", "fc_host"] | None = attr(name="type", default=None)
    name: str | None = attr(name="name", default=None)
    parent: str | None = attr(name="parent", default=None)
    managed: YesNo | None = attr(name="managed", default=None)
    parent_wwnn: str | None = attr(name="parent_wwnn", default=None)
    parent_wwpn: str | None = attr(name="parent_wwpn", default=None)
    parent_fabric_wwn: str | None = attr(name="parent_fabric_wwn", default=None)
    wwnn: str | None = attr(name="wwnn", default=None)
    wwpn: str | None = attr(name="wwpn", default=None)
    parentaddr: ScsiParentAddress | None = element(tag="parentaddr", default=None)


class Permissions(LibvirtXmlModel, tag="permissions"):
    """``<permissions>``: mode and ownership of a volume or a pool's target."""

    mode: str | None = element(tag="mode", default=None, description="Octal.")
    owner: str | None = element(
        tag="owner",
        default=None,
        pattern=r"^(-1|[0-9]+)$",
        description="User ID or ``-1``; kept as written (``0744`` stays ``0744``).",
    )
    group: str | None = element(
        tag="group", default=None, pattern=r"^(-1|[0-9]+)$", description="Group ID."
    )
    label: str | None = element(tag="label", default=None)


class Timestamps(LibvirtXmlModel, tag="timestamps"):
    """``<timestamps>``: access, birth, change and modification times."""

    atime: str | None = element(tag="atime", default=None)
    btime: str | None = element(tag="btime", default=None)
    ctime: str | None = element(tag="ctime", default=None)
    mtime: str | None = element(tag="mtime", default=None)


class DeviceSeclabel(LibvirtXmlModel, tag="seclabel"):
    """``<seclabel>`` of a device source: per-image security labelling."""

    model: str | None = attr(name="model", default=None)
    relabel: YesNo | None = attr(name="relabel", default=None)
    labelskip: YesNo | None = attr(name="labelskip", default=None)
    labels: list[str] = element(tag="label", default_factory=list)
