"""Models for ``<secret>`` XML. See https://libvirt.org/formatsecret.html"""

from libvirtpy.xml.secret.secret import (
    Secret,
    SecretUsage,
)

__all__ = [
    "Secret",
    "SecretUsage",
]
