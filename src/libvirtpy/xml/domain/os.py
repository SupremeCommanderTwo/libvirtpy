"""``<os>``: how the guest boots.

One ``Os`` model covers the BIOS/UEFI (``hvm``), Xen paravirtual (``xen``,
``linux``, ``xenpvh``) and container (``exe``) variants. They are told apart
by the *text* of ``<type>``, which a discriminated union cannot dispatch on;
libvirt's own ``virDomainOSDef`` is one structure as well.

``<nvram>`` is a union like ``<disk>``: it reuses the storage sources of
``libvirtpy.xml.domain.storage_source``.

See https://libvirt.org/formatdomain.html#operating-system-booting
"""

from typing import Literal

from pydantic import Field
from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OptionalText, YesNo
from libvirtpy.xml.domain.storage_source import (
    BlockStorage,
    CtlStorage,
    DirStorage,
    FileStorage,
    NetworkStorage,
    NvmeStorage,
    VhostUserStorage,
    VhostVdpaStorage,
    VolumeStorage,
)

__all__ = [
    "Bios",
    "BlockNvram",
    "Boot",
    "BootMenu",
    "CtlNvram",
    "DirNvram",
    "FileNvram",
    "InitEnv",
    "Loader",
    "NetworkNvram",
    "NvmeNvram",
    "Nvram",
    "Os",
    "OsAcpi",
    "OsAcpiTable",
    "OsFirmware",
    "OsFirmwareFeature",
    "OsType",
    "Smbios",
    "Varstore",
    "VhostUserNvram",
    "VhostVdpaNvram",
    "VolumeNvram",
]

PflashFormat = Literal["raw", "qcow2"]


class OsType(LibvirtXmlModel, tag="type"):
    """``<type>``: the kind of OS the guest runs."""

    value: Literal["hvm", "xen", "linux", "xenpvh", "exe"] = Field(
        description="Element text: ``hvm`` for full virtualization, ``xen``/"
        "``linux``/``xenpvh`` for Xen paravirtualization, ``exe`` for containers."
    )
    arch: str | None = attr(
        name="arch", default=None, description="CPU architecture, e.g. ``x86_64``."
    )
    machine: str | None = attr(
        name="machine", default=None, description="Machine type, e.g. ``q35``."
    )


class OsFirmwareFeature(LibvirtXmlModel, tag="feature"):
    """``<feature>`` in ``<os><firmware>``. Since 7.2.0."""

    enabled: YesNo = attr(name="enabled")
    name: Literal["enrolled-keys", "secure-boot"] = attr(name="name")


class OsFirmware(LibvirtXmlModel, tag="firmware"):
    """``<firmware>``: requirements for automatic firmware selection."""

    features: list[OsFirmwareFeature] = element(tag="feature", default_factory=list)


class Loader(LibvirtXmlModel, tag="loader"):
    """``<loader>``: the firmware image (BIOS or UEFI)."""

    value: OptionalText = Field(
        default=None, description="Element text: absolute path of the image."
    )
    readonly: YesNo | None = attr(name="readonly", default=None)
    secure: YesNo | None = attr(
        name="secure", default=None, description="Secure Boot capable. Since 2.1.0."
    )
    type: Literal["rom", "pflash"] | None = attr(name="type", default=None)
    stateless: YesNo | None = attr(
        name="stateless", default=None, description="No NVRAM store. Since 8.6.0."
    )
    format: PflashFormat | None = attr(name="format", default=None)


class _NvramBase(LibvirtXmlModel, tag="nvram"):
    """``<nvram>``: the UEFI variable store (attributes of every kind)."""

    value: OptionalText = Field(
        default=None,
        description="Element text: absolute path of the store (a file store).",
    )
    template: str | None = attr(
        name="template", default=None, description="Master copy of the store."
    )
    template_format: PflashFormat | None = attr(name="templateFormat", default=None)
    format: PflashFormat | None = attr(name="format", default=None)


class FileNvram(_NvramBase, FileStorage, tag="nvram"):
    """A file store: ``<nvram>/path</nvram>`` or ``<nvram type='file'>``."""


class BlockNvram(_NvramBase, BlockStorage, tag="nvram"):
    """``<nvram type='block'>``."""


class DirNvram(_NvramBase, DirStorage, tag="nvram"):
    """``<nvram type='dir'>``."""


class NetworkNvram(_NvramBase, NetworkStorage, tag="nvram"):
    """``<nvram type='network'>``."""


class VolumeNvram(_NvramBase, VolumeStorage, tag="nvram"):
    """``<nvram type='volume'>``."""


class NvmeNvram(_NvramBase, NvmeStorage, tag="nvram"):
    """``<nvram type='nvme'>``."""


class VhostUserNvram(_NvramBase, VhostUserStorage, tag="nvram"):
    """``<nvram type='vhostuser'>``."""


class VhostVdpaNvram(_NvramBase, VhostVdpaStorage, tag="nvram"):
    """``<nvram type='vhostvdpa'>``."""


class CtlNvram(_NvramBase, CtlStorage, tag="nvram"):
    """``<nvram type='ctl'>``."""


Nvram = (
    FileNvram
    | BlockNvram
    | DirNvram
    | NetworkNvram
    | VolumeNvram
    | NvmeNvram
    | VhostUserNvram
    | VhostVdpaNvram
    | CtlNvram
)
"""Any ``<nvram>``; the variant is chosen by its ``type`` attribute."""


class Varstore(LibvirtXmlModel, tag="varstore"):
    """``<varstore>``: UEFI variables kept by the hypervisor. Since 12.1.0 (QEMU)."""

    template: str | None = attr(name="template", default=None)
    path: str | None = attr(name="path", default=None)


class Boot(LibvirtXmlModel, tag="boot"):
    """``<boot>``: one device in the BIOS boot order."""

    dev: Literal["hd", "fd", "cdrom", "network"] = attr(name="dev")


class BootMenu(LibvirtXmlModel, tag="bootmenu"):
    """``<bootmenu>``: the interactive boot menu."""

    enable: YesNo = attr(name="enable")
    timeout: int | None = attr(
        name="timeout", default=None, ge=0, le=65535, description="Milliseconds."
    )


class Smbios(LibvirtXmlModel, tag="smbios"):
    """``<smbios>``: where the guest's SMBIOS data comes from."""

    mode: Literal["emulate", "host", "sysinfo"] = attr(name="mode")


class Bios(LibvirtXmlModel, tag="bios"):
    """``<bios>``: BIOS settings."""

    useserial: YesNo | None = attr(
        name="useserial", default=None, description="Serial Graphics Adapter."
    )
    reboot_timeout: int | None = attr(
        name="rebootTimeout",
        default=None,
        ge=-1,
        le=65535,
        description="Milliseconds before rebooting after a failed boot; -1 never.",
    )


class OsAcpiTable(LibvirtXmlModel, tag="table"):
    """``<table>`` in ``<os><acpi>``: an extra ACPI table for the guest."""

    value: str = Field(description="Element text: absolute path of the table.")
    type: Literal["raw", "rawset", "slic", "msdm"] = attr(name="type")


class OsAcpi(LibvirtXmlModel, tag="acpi"):
    """``<acpi>`` in ``<os>``: extra ACPI tables."""

    tables: list[OsAcpiTable] = element(tag="table", default_factory=list)


class InitEnv(LibvirtXmlModel, tag="initenv"):
    """``<initenv>``: an environment variable for a container's init."""

    value: str = Field(default="", description="Element text: the value.")
    name: str = attr(name="name")


class Os(LibvirtXmlModel, tag="os"):
    """``<os>``: firmware, boot order and direct kernel boot."""

    firmware: Literal["bios", "efi"] | None = attr(
        name="firmware",
        default=None,
        description="Select the firmware automatically. Since 5.2.0.",
    )
    type: OsType = element(tag="type")
    firmware_info: OsFirmware | None = element(tag="firmware", default=None)
    loader: Loader | None = element(tag="loader", default=None)
    nvram: Nvram | None = element(tag="nvram", default=None)
    varstore: Varstore | None = element(tag="varstore", default=None)
    boots: list[Boot] = element(tag="boot", default_factory=list)
    boot_menu: BootMenu | None = element(tag="bootmenu", default=None)
    smbios: Smbios | None = element(tag="smbios", default=None)
    bios: Bios | None = element(tag="bios", default=None)
    acpi: OsAcpi | None = element(tag="acpi", default=None)

    # Direct kernel boot
    kernel: str | None = element(tag="kernel", default=None)
    initrd: str | None = element(tag="initrd", default=None)
    root: str | None = element(tag="root", default=None)
    cmdline: str | None = element(tag="cmdline", default=None)
    shim: str | None = element(tag="shim", default=None)
    dtb: str | None = element(tag="dtb", default=None)

    # Container boot (type ``exe``)
    init: str | None = element(tag="init", default=None)
    init_args: list[str] = element(tag="initarg", default_factory=list)
    init_envs: list[InitEnv] = element(tag="initenv", default_factory=list)
    init_dir: str | None = element(tag="initdir", default=None)
    init_user: str | None = element(tag="inituser", default=None)
    init_group: str | None = element(tag="initgroup", default=None)
