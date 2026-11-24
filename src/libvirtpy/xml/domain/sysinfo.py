"""``<sysinfo>`` of a domain: SMBIOS data or firmware configuration entries.

The standalone host ``<sysinfo>`` document is ``libvirtpy.xml.sysinfo``.

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
    SysinfoOemStrings,
    SysinfoSystem,
)

__all__ = ["Sysinfo"]


class Sysinfo(LibvirtXmlModel, tag="sysinfo"):
    """``<sysinfo>``: ``type='smbios'`` groups, or ``type='fwcfg'`` entries."""

    type: Literal["smbios", "fwcfg"] = attr(name="type")
    bios: SysinfoBios | None = element(tag="bios", default=None)
    system: SysinfoSystem | None = element(tag="system", default=None)
    base_boards: list[SysinfoBaseBoard] = element(tag="baseBoard", default_factory=list)
    chassis: SysinfoChassis | None = element(tag="chassis", default=None)
    oem_strings: SysinfoOemStrings | None = element(tag="oemStrings", default=None)
    entries: list[FwcfgEntry] = element(tag="entry", default_factory=list)
