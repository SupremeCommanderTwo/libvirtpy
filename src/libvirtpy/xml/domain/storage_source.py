"""Storage sources: what a ``<disk>``, ``<backingStore>`` or ``<nvram>`` reads.

The ``<source>`` element has a different shape per ``type`` of its *parent*
(``<disk type='file'>`` has ``<source file=...>``, ``type='block'`` has
``<source dev=...>``). The ``<source>`` itself carries no discriminator, so
parents cannot use a union of sources directly. Instead each kind of storage
is a small mixin (``FileStorage``, ``BlockStorage``, ...) that adds the parent's
``type`` literal and the matching ``source``. A parent builds one class per
mixin and a plain union of them (see ``libvirtpy.xml.domain.devices.disk``).

All network protocols share one ``NetworkSource`` model: they differ by which
optional children they allow, which is a constraint libvirt checks, not a
different structure.

See https://libvirt.org/formatdomain.html#hard-drives-floppy-disks-cdroms
"""

from typing import Literal

from pydantic import Field
from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._shared.storage import (
    DeviceSeclabel,
    StorageEncryption,
    StorageSecret,
)
from libvirtpy.xml._types import HexNumber, OnOff, SizeUnit, YesNo

__all__ = [
    "BlockDataStore",
    "BlockSource",
    "BlockStorage",
    "CookieList",
    "CtlDataStore",
    "CtlSource",
    "CtlStorage",
    "DataStore",
    "DeviceSeclabel",
    "DirDataStore",
    "DirSource",
    "DirStorage",
    "DiskFormat",
    "FileDataStore",
    "FileSource",
    "FileStorage",
    "MetadataCache",
    "MetadataCacheMaxSize",
    "NetworkAuth",
    "NetworkDataStore",
    "NetworkHost",
    "NetworkSource",
    "NetworkStorage",
    "NvmeAddress",
    "NvmeDataStore",
    "NvmeSource",
    "NvmeStorage",
    "Reconnect",
    "ReservationSource",
    "Reservations",
    "SourceSlice",
    "SourceSlices",
    "VhostUserDataStore",
    "VhostUserSource",
    "VhostUserStorage",
    "VhostVdpaDataStore",
    "VhostVdpaSource",
    "VhostVdpaStorage",
    "VolumeDataStore",
    "VolumeSource",
    "VolumeStorage",
]

StartupPolicy = Literal["mandatory", "requisite", "optional"]


class SourceSlice(LibvirtXmlModel, tag="slice"):
    """``<slice>``: a part of the storage the guest sees."""

    type: Literal["storage"] = attr(name="type")
    offset: int = attr(name="offset", ge=0)
    size: int = attr(name="size", ge=1)


class SourceSlices(LibvirtXmlModel, tag="slices"):
    slices: list[SourceSlice] = element(tag="slice", default_factory=list)


class Reconnect(LibvirtXmlModel, tag="reconnect"):
    """``<reconnect>``: reconnection to a socket server."""

    enabled: YesNo | None = attr(name="enabled", default=None)
    timeout: int | None = attr(name="timeout", default=None, ge=0)
    delay: int | None = attr(name="delay", default=None, ge=0)


class MetadataCacheMaxSize(LibvirtXmlModel, tag="max_size"):
    """``<max_size>``: limit of the qcow2 metadata cache."""

    value: int = Field(ge=0, description="Element text: the amount, in ``unit``.")
    unit: SizeUnit | None = attr(name="unit", default=None)


class MetadataCache(LibvirtXmlModel, tag="metadata_cache"):
    max_size: MetadataCacheMaxSize | None = element(tag="max_size", default=None)


class DiskFormat(LibvirtXmlModel, tag="format"):
    """``<format>``: the image format of a storage source."""

    type: str = attr(name="type", description="Image format, e.g. ``qcow2``.")
    metadata_cache: MetadataCache | None = element(tag="metadata_cache", default=None)


class ReservationSource(LibvirtXmlModel, tag="source"):
    """``<source>`` of ``<reservations>``: the persistent reservations helper."""

    type: Literal["unix"] = attr(name="type")
    path: str = attr(name="path")
    mode: Literal["server", "client"] = attr(name="mode")
    reconnect: Reconnect | None = element(tag="reconnect", default=None)


class Reservations(LibvirtXmlModel, tag="reservations"):
    """``<reservations>``: SCSI persistent reservations. Since 4.4.0."""

    managed: YesNo | None = attr(name="managed", default=None)
    migration: YesNo | None = attr(name="migration", default=None)
    source: ReservationSource | None = element(tag="source", default=None)


class _StorageSourceBase(LibvirtXmlModel, tag="source"):
    """Attributes and children common to most ``<source>`` kinds."""

    index: int | None = attr(
        name="index", default=None, ge=1, description="Backing chain index."
    )
    startup_policy: StartupPolicy | None = attr(name="startupPolicy", default=None)
    slices: SourceSlices | None = element(tag="slices", default=None)
    encryption: StorageEncryption | None = element(tag="encryption", default=None)
    seclabels: list[DeviceSeclabel] = element(tag="seclabel", default_factory=list)
    data_store: DataStore | None = element(tag="dataStore", default=None)


class FileSource(_StorageSourceBase, tag="source"):
    """``<source file=...>`` of a ``type='file'`` parent."""

    file: str | None = attr(name="file", default=None)
    fdgroup: str | None = attr(
        name="fdgroup", default=None, description="Passed file descriptors."
    )


class BlockSource(_StorageSourceBase, tag="source"):
    """``<source dev=...>`` of a ``type='block'`` parent."""

    dev: str | None = attr(name="dev", default=None)
    reservations: Reservations | None = element(tag="reservations", default=None)


class DirSource(_StorageSourceBase, tag="source"):
    """``<source dir=...>`` of a ``type='dir'`` parent."""

    dir: str = attr(name="dir")


class VolumeSource(_StorageSourceBase, tag="source"):
    """``<source pool=... volume=...>`` of a ``type='volume'`` parent."""

    pool: str = attr(name="pool")
    volume: str = attr(name="volume")
    mode: Literal["host", "direct"] | None = attr(name="mode", default=None)


class NvmeAddress(LibvirtXmlModel, tag="address"):
    """``<address>`` of an NVMe source: a PCI address without a ``type``."""

    domain: HexNumber | None = attr(name="domain", default=None)
    bus: HexNumber | None = attr(name="bus", default=None)
    slot: HexNumber | None = attr(name="slot", default=None)
    function: HexNumber | None = attr(name="function", default=None)
    multifunction: OnOff | None = attr(name="multifunction", default=None)


class NvmeSource(_StorageSourceBase, tag="source"):
    """``<source type='pci' ...>`` of a ``type='nvme'`` parent. Since 6.0.0."""

    type: Literal["pci"] = attr(name="type")
    namespace: int = attr(name="namespace", ge=0)
    managed: YesNo | None = attr(name="managed", default=None)
    address: NvmeAddress = element(tag="address")


class VhostUserSource(LibvirtXmlModel, tag="source"):
    """``<source type='unix' ...>`` of a ``type='vhostuser'`` parent."""

    type: Literal["unix"] = attr(name="type")
    path: str = attr(name="path")
    reconnect: Reconnect | None = element(tag="reconnect", default=None)


class VhostVdpaSource(LibvirtXmlModel, tag="source"):
    """``<source dev=...>`` of a ``type='vhostvdpa'`` parent."""

    dev: str = attr(name="dev")


class CtlSource(LibvirtXmlModel, tag="source"):
    """``<source dev=...>`` of a ``type='ctl'`` parent."""

    dev: str = attr(name="dev")


class NetworkHost(LibvirtXmlModel, tag="host"):
    """``<host>``: a server of a network disk."""

    transport: Literal["tcp", "rdma", "unix"] | None = attr(
        name="transport", default=None
    )
    name: str | None = attr(name="name", default=None)
    port: int | None = attr(name="port", default=None, ge=0)
    socket: str | None = attr(name="socket", default=None, description="Unix only.")


class NetworkAuth(LibvirtXmlModel, tag="auth"):
    """``<auth>``: credentials for a network disk."""

    username: str = attr(name="username")
    secret: StorageSecret = element(tag="secret")


class SnapshotName(LibvirtXmlModel, tag="snapshot"):
    name: str = attr(name="name")


class ConfigFile(LibvirtXmlModel, tag="config"):
    file: str = attr(name="file")


class InitiatorIqn(LibvirtXmlModel, tag="iqn"):
    name: str = attr(name="name")


class Initiator(LibvirtXmlModel, tag="initiator"):
    """``<initiator>``: the iSCSI initiator name."""

    iqn: InitiatorIqn = element(tag="iqn")


class Cookie(LibvirtXmlModel, tag="cookie"):
    value: str = Field(description="Element text: the cookie value.")
    name: str = attr(name="name")


class CookieList(LibvirtXmlModel, tag="cookies"):
    cookies: list[Cookie] = element(tag="cookie", default_factory=list)


class Readahead(LibvirtXmlModel, tag="readahead"):
    size: int = attr(name="size", ge=1)


class NetworkTimeout(LibvirtXmlModel, tag="timeout"):
    seconds: int = attr(name="seconds", ge=1)


class SslVerify(LibvirtXmlModel, tag="ssl"):
    verify: YesNo = attr(name="verify")


class KnownHosts(LibvirtXmlModel, tag="knownHosts"):
    path: str = attr(name="path")


class NetworkIdentity(LibvirtXmlModel, tag="identity"):
    """``<identity>``: SSH credentials, or the user and group of an NFS disk."""

    username: str | None = attr(name="username", default=None)
    keyfile: str | None = attr(name="keyfile", default=None)
    agentsock: str | None = attr(name="agentsock", default=None)
    user: str | None = attr(name="user", default=None)
    group: str | None = attr(name="group", default=None)


class NetworkSource(_StorageSourceBase, tag="source"):
    """``<source protocol=...>`` of a ``type='network'`` parent."""

    protocol: Literal[
        "nbd",
        "gluster",
        "rbd",
        "iscsi",
        "http",
        "https",
        "ftps",
        "ftp",
        "ssh",
        "sheepdog",
        "tftp",
        "vxhs",
        "nfs",
    ] = attr(name="protocol")
    name: str | None = attr(name="name", default=None)
    query: str | None = attr(name="query", default=None)
    tls: YesNo | None = attr(name="tls", default=None)
    tls_hostname: str | None = attr(name="tlsHostname", default=None)
    hosts: list[NetworkHost] = element(tag="host", default_factory=list)
    reconnect: Reconnect | None = element(tag="reconnect", default=None)
    snapshot: SnapshotName | None = element(tag="snapshot", default=None)
    config: ConfigFile | None = element(tag="config", default=None)
    auth: NetworkAuth | None = element(tag="auth", default=None)
    initiator: Initiator | None = element(tag="initiator", default=None)
    cookies: CookieList | None = element(tag="cookies", default=None)
    ssl: SslVerify | None = element(tag="ssl", default=None)
    readahead: Readahead | None = element(tag="readahead", default=None)
    timeout: NetworkTimeout | None = element(tag="timeout", default=None)
    known_hosts: KnownHosts | None = element(tag="knownHosts", default=None)
    identity: NetworkIdentity | None = element(tag="identity", default=None)


class FileStorage(LibvirtXmlModel):
    """Mixin: ``type='file'``, which is also the default when ``type`` is missing."""

    type: Literal["file"] | None = attr(name="type", default=None)
    source: FileSource | None = element(tag="source", default=None)


class BlockStorage(LibvirtXmlModel):
    """Mixin: ``type='block'``."""

    type: Literal["block"] = attr(name="type")
    source: BlockSource | None = element(tag="source", default=None)


class DirStorage(LibvirtXmlModel):
    """Mixin: ``type='dir'``."""

    type: Literal["dir"] = attr(name="type")
    source: DirSource | None = element(tag="source", default=None)


class NetworkStorage(LibvirtXmlModel):
    """Mixin: ``type='network'``."""

    type: Literal["network"] = attr(name="type")
    source: NetworkSource | None = element(tag="source", default=None)


class VolumeStorage(LibvirtXmlModel):
    """Mixin: ``type='volume'``."""

    type: Literal["volume"] = attr(name="type")
    source: VolumeSource | None = element(tag="source", default=None)


class NvmeStorage(LibvirtXmlModel):
    """Mixin: ``type='nvme'``."""

    type: Literal["nvme"] = attr(name="type")
    source: NvmeSource | None = element(tag="source", default=None)


class VhostUserStorage(LibvirtXmlModel):
    """Mixin: ``type='vhostuser'``."""

    type: Literal["vhostuser"] = attr(name="type")
    source: VhostUserSource | None = element(tag="source", default=None)


class VhostVdpaStorage(LibvirtXmlModel):
    """Mixin: ``type='vhostvdpa'``."""

    type: Literal["vhostvdpa"] = attr(name="type")
    source: VhostVdpaSource | None = element(tag="source", default=None)


class CtlStorage(LibvirtXmlModel):
    """Mixin: ``type='ctl'``."""

    type: Literal["ctl"] = attr(name="type")
    source: CtlSource | None = element(tag="source", default=None)


class _DataStoreBase(LibvirtXmlModel, tag="dataStore"):
    """``<dataStore>``: where the guest data of a qcow2 image is stored."""

    format_info: DiskFormat | None = element(tag="format", default=None)


class FileDataStore(_DataStoreBase, FileStorage, tag="dataStore"):
    """A ``<dataStore>`` that is a file."""


class BlockDataStore(_DataStoreBase, BlockStorage, tag="dataStore"):
    """A ``<dataStore type='block'>``."""


class DirDataStore(_DataStoreBase, DirStorage, tag="dataStore"):
    """A ``<dataStore type='dir'>``."""


class NetworkDataStore(_DataStoreBase, NetworkStorage, tag="dataStore"):
    """A ``<dataStore type='network'>``."""


class VolumeDataStore(_DataStoreBase, VolumeStorage, tag="dataStore"):
    """A ``<dataStore type='volume'>``."""


class NvmeDataStore(_DataStoreBase, NvmeStorage, tag="dataStore"):
    """A ``<dataStore type='nvme'>``."""


class VhostUserDataStore(_DataStoreBase, VhostUserStorage, tag="dataStore"):
    """A ``<dataStore type='vhostuser'>``."""


class VhostVdpaDataStore(_DataStoreBase, VhostVdpaStorage, tag="dataStore"):
    """A ``<dataStore type='vhostvdpa'>``."""


class CtlDataStore(_DataStoreBase, CtlStorage, tag="dataStore"):
    """A ``<dataStore type='ctl'>``."""


DataStore = (
    FileDataStore
    | BlockDataStore
    | DirDataStore
    | NetworkDataStore
    | VolumeDataStore
    | NvmeDataStore
    | VhostUserDataStore
    | VhostVdpaDataStore
    | CtlDataStore
)
"""Any ``<dataStore>``; the variant is chosen by its ``type`` attribute."""

# The sources refer to ``DataStore``, which is defined after them and uses them
# through the mixins: every class of this cycle has to be rebuilt once all of
# them exist, or pydantic-xml leaves their serializers unbuilt.
FileSource.model_rebuild()
BlockSource.model_rebuild()
DirSource.model_rebuild()
VolumeSource.model_rebuild()
NvmeSource.model_rebuild()
NetworkSource.model_rebuild()
FileStorage.model_rebuild()
BlockStorage.model_rebuild()
DirStorage.model_rebuild()
NetworkStorage.model_rebuild()
VolumeStorage.model_rebuild()
NvmeStorage.model_rebuild()
VhostUserStorage.model_rebuild()
VhostVdpaStorage.model_rebuild()
CtlStorage.model_rebuild()
FileDataStore.model_rebuild()
BlockDataStore.model_rebuild()
DirDataStore.model_rebuild()
NetworkDataStore.model_rebuild()
VolumeDataStore.model_rebuild()
NvmeDataStore.model_rebuild()
VhostUserDataStore.model_rebuild()
VhostVdpaDataStore.model_rebuild()
CtlDataStore.model_rebuild()
