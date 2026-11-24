"""``<secret>``: a secret value (passphrase, key) kept by libvirt.

See https://libvirt.org/formatsecret.html
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import Uuid, YesNo

__all__ = ["Secret", "SecretUsage"]


class SecretUsage(LibvirtXmlModel, tag="usage"):
    """``<usage>``: what the secret is for.

    The usage ``type`` decides which child names the user: ``volume`` has a
    ``<volume>`` path, ``iscsi`` a ``<target>``, the others a ``<name>``.
    """

    type: Literal["volume", "ceph", "iscsi", "tls", "vtpm"] = attr(name="type")
    volume: str | None = element(tag="volume", default=None)
    name: str | None = element(tag="name", default=None)
    target: str | None = element(tag="target", default=None)


class Secret(LibvirtXmlModel, tag="secret"):
    """``<secret>``: metadata of a secret (the value itself is not in the XML)."""

    ephemeral: YesNo | None = attr(name="ephemeral", default=None)
    private: YesNo | None = attr(name="private", default=None)
    uuid: Uuid | None = element(tag="uuid", default=None)
    description: str | None = element(tag="description", default=None)
    usage: SecretUsage | None = element(tag="usage", default=None)
