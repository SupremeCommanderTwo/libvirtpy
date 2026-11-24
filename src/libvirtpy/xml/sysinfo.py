"""``<sysinfo>`` as a standalone document: the host's SMBIOS data.

A domain's ``<sysinfo>`` is a subset of it (``libvirtpy.xml.domain.Sysinfo``).

See https://libvirt.org/formatdomain.html#smbios-system-information
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.sysinfo import (
    FwcfgEntry,
    SysinfoBaseBoard,
    SysinfoBios,
    SysinfoChassis,
    SysinfoMemoryDevice,
    SysinfoOemStrings,
    SysinfoProcessor,
    SysinfoSystem,
)

__all__ = ["Sysinfo"]


class Sysinfo(LibvirtXmlModel, tag="sysinfo"):
    """``<sysinfo>``: SMBIOS groups, or ``type='fwcfg'`` entries."""

    type: Literal["smbios", "fwcfg"] = attr(name="type")
    bios: SysinfoBios | None = element(tag="bios", default=None)
    system: SysinfoSystem | None = element(tag="system", default=None)
    base_boards: list[SysinfoBaseBoard] = element(tag="baseBoard", default_factory=list)
    chassis: SysinfoChassis | None = element(tag="chassis", default=None)
    processors: list[SysinfoProcessor] = element(tag="processor", default_factory=list)
    memory_devices: list[SysinfoMemoryDevice] = element(
        tag="memory_device", default_factory=list
    )
    oem_strings: SysinfoOemStrings | None = element(tag="oemStrings", default=None)
    entries: list[FwcfgEntry] = element(tag="entry", default_factory=list)
