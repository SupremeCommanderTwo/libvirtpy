"""Read-only capability documents. See https://libvirt.org/formatcaps.html"""

from libvirtpy.xml.capabilities.domain import (
    CapsEnum,
    DomainCapabilities,
    FeatureSupport,
)
from libvirtpy.xml.capabilities.host import (
    Capabilities,
    GuestArch,
    GuestCapabilities,
    GuestDomain,
    HostCapabilities,
    HostCpu,
    HostTopology,
    SecModel,
)
from libvirtpy.xml.capabilities.storagepool import (
    PoolCapabilities,
    PoolCapsDefaultFormat,
    PoolCapsEnum,
    PoolCapsOptions,
    StoragePoolCapabilities,
)

__all__ = [
    "Capabilities",
    "CapsEnum",
    "DomainCapabilities",
    "FeatureSupport",
    "GuestArch",
    "GuestCapabilities",
    "GuestDomain",
    "HostCapabilities",
    "HostCpu",
    "HostTopology",
    "PoolCapabilities",
    "PoolCapsDefaultFormat",
    "PoolCapsEnum",
    "PoolCapsOptions",
    "SecModel",
    "StoragePoolCapabilities",
]
