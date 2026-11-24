"""Pydantic models that parse and generate libvirt XML.

The root of every document type is re-exported here; its parts live in the
package of the document (``libvirtpy.xml.domain``, ``libvirtpy.xml.network``, ...).
"""

from libvirtpy.errors import LibvirtPyError
from libvirtpy.xml._types import OnOff, PresenceFlag, SizeUnit, Uuid, YesNo
from libvirtpy.xml.backup import Backup, Checkpoint
from libvirtpy.xml.capabilities import (
    Capabilities,
    DomainCapabilities,
    StoragePoolCapabilities,
)
from libvirtpy.xml.domain import Domain
from libvirtpy.xml.interface import HostInterface
from libvirtpy.xml.network import Network, NetworkPort
from libvirtpy.xml.nodedev import Device
from libvirtpy.xml.nwfilter import Filter, FilterBinding
from libvirtpy.xml.secret import Secret
from libvirtpy.xml.snapshot import Snapshot
from libvirtpy.xml.storage import Pool, Volume
from libvirtpy.xml.sysinfo import Sysinfo

__all__ = [
    "Backup",
    "Capabilities",
    "Checkpoint",
    "Device",
    "Domain",
    "DomainCapabilities",
    "Filter",
    "FilterBinding",
    "HostInterface",
    "LibvirtPyError",
    "Network",
    "NetworkPort",
    "OnOff",
    "Pool",
    "PresenceFlag",
    "Secret",
    "SizeUnit",
    "Snapshot",
    "StoragePoolCapabilities",
    "Sysinfo",
    "Uuid",
    "Volume",
    "YesNo",
]
