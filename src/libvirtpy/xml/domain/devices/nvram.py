"""``<nvram>`` device: the NVRAM of PowerPC guests.

Not to be confused with ``<os><nvram>``, the UEFI variable store
(``libvirtpy.xml.domain.os``).

See https://libvirt.org/formatdomain.html#nvram-device
"""

from pydantic_xml import element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml.domain.devices.address import Address

__all__ = ["NvramDevice"]


class NvramDevice(LibvirtXmlModel, tag="nvram"):
    """``<nvram>``: a non-volatile RAM device."""

    address: Address | None = element(tag="address", default=None)
