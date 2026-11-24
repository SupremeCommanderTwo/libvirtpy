"""``<seclabel>``: the security label of the guest process.

``<seclabel>`` inside a device source is a different element
(``DeviceSeclabel`` in ``libvirtpy.xml.domain.storage_source``).

See https://libvirt.org/formatdomain.html#security-label
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import YesNo

__all__ = ["Seclabel"]


class Seclabel(LibvirtXmlModel, tag="seclabel"):
    """``<seclabel>``: how the guest is labelled by a security driver."""

    model: str | None = attr(
        name="model", default=None, description="The driver, e.g. ``selinux``."
    )
    type: Literal["dynamic", "static", "none"] | None = attr(name="type", default=None)
    relabel: YesNo | None = attr(name="relabel", default=None)
    label: str | None = element(tag="label", default=None)
    imagelabel: str | None = element(tag="imagelabel", default=None)
    baselabel: str | None = element(tag="baselabel", default=None)
