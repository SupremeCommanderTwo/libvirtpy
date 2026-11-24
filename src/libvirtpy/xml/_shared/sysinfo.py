"""The ``<sysinfo>`` building blocks shared by a domain and the host document.

See https://libvirt.org/formatdomain.html#smbios-system-information
"""

from pydantic import Field
from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OptionalText

__all__ = [
    "FwcfgEntry",
    "OemStringEntry",
    "SmbiosEntry",
    "SysinfoBaseBoard",
    "SysinfoBios",
    "SysinfoChassis",
    "SysinfoGroup",
    "SysinfoMemoryDevice",
    "SysinfoOemStrings",
    "SysinfoProcessor",
    "SysinfoSystem",
]


class SmbiosEntry(LibvirtXmlModel, tag="entry"):
    """``<entry>`` of an SMBIOS group: one named field."""

    value: str = Field(default="", description="Element text: the value.")
    name: str = attr(name="name")


class OemStringEntry(LibvirtXmlModel, tag="entry"):
    """``<entry>`` of ``<oemStrings>``: one string, without a name."""

    value: str = Field(default="", description="Element text: the string.")


class FwcfgEntry(LibvirtXmlModel, tag="entry"):
    """``<entry>`` of a ``fwcfg`` sysinfo: a named item from text or a file."""

    value: OptionalText = Field(
        default=None, description="Element text: the value (absent with ``file``)."
    )
    name: str = attr(name="name")
    file: str | None = attr(name="file", default=None)


class SysinfoGroup(LibvirtXmlModel):
    """Base of the SMBIOS groups: a list of named ``<entry>`` elements."""

    entries: list[SmbiosEntry] = element(tag="entry", default_factory=list)


class SysinfoBios(SysinfoGroup, tag="bios"):
    """``<bios>``: SMBIOS type 0."""


class SysinfoSystem(SysinfoGroup, tag="system"):
    """``<system>``: SMBIOS type 1."""


class SysinfoBaseBoard(SysinfoGroup, tag="baseBoard"):
    """``<baseBoard>``: SMBIOS type 2."""


class SysinfoChassis(SysinfoGroup, tag="chassis"):
    """``<chassis>``: SMBIOS type 3."""


class SysinfoOemStrings(LibvirtXmlModel, tag="oemStrings"):
    """``<oemStrings>``: SMBIOS type 11."""

    entries: list[OemStringEntry] = element(tag="entry", default_factory=list)


class SysinfoProcessor(SysinfoGroup, tag="processor"):
    """``<processor>``: SMBIOS type 4. Host document only."""


class SysinfoMemoryDevice(SysinfoGroup, tag="memory_device"):
    """``<memory_device>``: SMBIOS type 17. Host document only."""
