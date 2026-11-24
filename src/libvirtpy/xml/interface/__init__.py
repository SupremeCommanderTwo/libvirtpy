"""Models for host ``<interface>`` XML. See https://libvirt.org/formatinterface.html"""

from libvirtpy.xml.interface.interface import (
    HostInterface,
    HostInterfaceBond,
    HostInterfaceBridge,
    HostInterfaceVlan,
    InterfaceProtocol,
)

__all__ = [
    "HostInterface",
    "HostInterfaceBond",
    "HostInterfaceBridge",
    "HostInterfaceVlan",
    "InterfaceProtocol",
]
