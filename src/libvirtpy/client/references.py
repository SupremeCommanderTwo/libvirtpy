"""References: the ways a caller can name an object.

``client.lookup_domain(x)`` and ``client.start_domain(x)`` accept any
``DomainRef``: a runtime id (``int``), a name or UUID text (``str``), a
``uuid.UUID``, or a ``libvirtpy.xml.Domain`` model (resolved by its UUID, else its
name). Text that looks like a UUID is looked up by UUID, anything else by name.
"""

import re
from uuid import UUID

from libvirtpy.client.transport import Handle, Request
from libvirtpy.xml.backup import Checkpoint
from libvirtpy.xml.domain import Domain
from libvirtpy.xml.interface import HostInterface
from libvirtpy.xml.network import Network, NetworkPort
from libvirtpy.xml.nodedev import Device
from libvirtpy.xml.nwfilter import Filter, FilterBinding
from libvirtpy.xml.secret import Secret
from libvirtpy.xml.snapshot import Snapshot
from libvirtpy.xml.storage import Pool, Volume

__all__ = [
    "CheckpointRef",
    "DomainRef",
    "HostInterfaceRef",
    "NetworkPortRef",
    "NetworkRef",
    "NodeDeviceRef",
    "NwFilterBindingRef",
    "NwFilterRef",
    "PoolRef",
    "SecretRef",
    "SnapshotRef",
    "VolumeRef",
    "domain_lookup",
    "host_interface_lookup",
    "network_lookup",
    "node_device_lookup",
    "nwfilter_lookup",
    "pool_lookup",
    "secret_lookup",
    "snapshot_lookup",
    "volume_lookup",
]

type DomainRef = int | str | UUID | Domain
type NetworkRef = str | UUID | Network
type PoolRef = str | UUID | Pool
type VolumeRef = str | Volume
type SecretRef = str | UUID | Secret
type NwFilterRef = str | UUID | Filter
type HostInterfaceRef = str | HostInterface
type NodeDeviceRef = str | Device
type SnapshotRef = str | Snapshot
type CheckpointRef = str | Checkpoint
type NetworkPortRef = str | UUID | NetworkPort
type NwFilterBindingRef = str | FilterBinding

_UUID_TEXT = re.compile(
    r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}"
)


def domain_lookup(reference: DomainRef) -> Request:
    """Build the request that finds a domain.

    :param reference: a runtime id, name, UUID or ``Domain`` model.
    :returns: the lookup request.
    """
    if isinstance(reference, int) and not isinstance(reference, bool):
        return Request("domain_lookup_by_id", {"id": reference})
    return _lookup_by_name_or_uuid("domain", reference)


def network_lookup(reference: NetworkRef) -> Request:
    """Build the request that finds a network.

    :param reference: a name, UUID or ``Network`` model.
    :returns: the lookup request.
    """
    return _lookup_by_name_or_uuid("network", reference)


def pool_lookup(reference: PoolRef) -> Request:
    """Build the request that finds a storage pool.

    :param reference: a name, UUID or ``Pool`` model.
    :returns: the lookup request.
    """
    return _lookup_by_name_or_uuid("storage_pool", reference)


def nwfilter_lookup(reference: NwFilterRef) -> Request:
    """Build the request that finds a network filter.

    :param reference: a name, UUID or ``Filter`` model.
    :returns: the lookup request.
    """
    return _lookup_by_name_or_uuid("nwfilter", reference)


def secret_lookup(reference: SecretRef) -> Request:
    """Build the request that finds a secret (by UUID).

    :param reference: a UUID (as text or ``UUID``) or a ``Secret`` model.
    :returns: the lookup request.
    :raises TypeError: if the reference has no UUID.
    """
    uuid_text = _uuid_text(reference)
    if uuid_text is None:
        raise TypeError(f"a secret is found by UUID, not by {reference!r}")
    return Request("secret_lookup_by_uuid", {"uuid": uuid_text})


def host_interface_lookup(reference: HostInterfaceRef) -> Request:
    """Build the request that finds a host network interface.

    :param reference: a device name or MAC address, or a ``HostInterface`` model.
    :returns: the lookup request.
    """
    if isinstance(reference, HostInterface):
        return Request("interface_lookup_by_name", {"name": reference.name})
    if re.fullmatch(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", reference):
        return Request("interface_lookup_by_mac_string", {"mac": reference})
    return Request("interface_lookup_by_name", {"name": reference})


def node_device_lookup(reference: NodeDeviceRef) -> Request:
    """Build the request that finds a host device.

    :param reference: the device name (``pci_0000_00_1f_2``) or a ``Device`` model.
    :returns: the lookup request.
    """
    name = reference.name if isinstance(reference, Device) else reference
    return Request("node_device_lookup_by_name", {"name": name})


def volume_lookup(pool: Handle, reference: VolumeRef) -> Request:
    """Build the request that finds a volume of a pool.

    :param pool: the pool that holds the volume.
    :param reference: a name, a key or an absolute path, or a ``Volume`` model.
    :returns: the lookup request.
    """
    if isinstance(reference, Volume):
        if reference.key is not None:
            return Request("storage_vol_lookup_by_key", {"key": reference.key})
        return Request(
            "storage_vol_lookup_by_name", {"pool": pool, "name": reference.name}
        )
    if reference.startswith("/"):
        return Request("storage_vol_lookup_by_path", {"path": reference})
    return Request("storage_vol_lookup_by_name", {"pool": pool, "name": reference})


def snapshot_lookup(domain: Handle, reference: SnapshotRef) -> Request:
    """Build the request that finds a snapshot of a domain.

    :param domain: the domain that has the snapshot.
    :param reference: the snapshot name, or a ``Snapshot`` model.
    :returns: the lookup request.
    :raises TypeError: if a model has no name.
    """
    name = reference.name if isinstance(reference, Snapshot) else reference
    if name is None:
        raise TypeError("a snapshot is found by name; the model has none")
    return Request(
        "domain_snapshot_lookup_by_name",
        {"dom": domain, "name": name, "flags": 0},
    )


def checkpoint_lookup(domain: Handle, reference: CheckpointRef) -> Request:
    """Build the request that finds a checkpoint of a domain.

    :param domain: the domain that has the checkpoint.
    :param reference: the checkpoint name, or a ``Checkpoint`` model.
    :returns: the lookup request.
    :raises TypeError: if a model has no name.
    """
    name = reference.name if isinstance(reference, Checkpoint) else reference
    if name is None:
        raise TypeError("a checkpoint is found by name; the model has none")
    return Request(
        "domain_checkpoint_lookup_by_name",
        {"dom": domain, "name": name, "flags": 0},
    )


def network_port_lookup(network: Handle, reference: NetworkPortRef) -> Request:
    """Build the request that finds a port of a network.

    :param network: the network that has the port.
    :param reference: the port's UUID (text or ``UUID``), or a ``NetworkPort`` model.
    :returns: the lookup request.
    :raises TypeError: if the reference has no UUID.
    """
    uuid_text = _uuid_text(reference)
    if uuid_text is None:
        raise TypeError("a network port is found by UUID")
    return Request(
        "network_port_lookup_by_uuid", {"network": network, "uuid": uuid_text}
    )


def nwfilter_binding_lookup(reference: NwFilterBindingRef) -> Request:
    """Build the request that finds a network filter binding.

    :param reference: the name of the port device (``vnet0``) or a ``FilterBinding``.
    :returns: the lookup request.
    :raises TypeError: if a model has no port device.
    """
    if isinstance(reference, FilterBinding):
        if reference.portdev is None:
            raise TypeError("a binding is found by port device; the model has none")
        reference = reference.portdev.name
    return Request("nwfilter_binding_lookup_by_port_dev", {"name": reference})


def _lookup_by_name_or_uuid(prefix: str, reference: object) -> Request:
    """Build a ``<prefix>_lookup_by_uuid`` or ``<prefix>_lookup_by_name`` request.

    :param prefix: the object kind in the procedure name, e.g. ``"domain"``.
    :param reference: a UUID, a name or a model.
    :returns: the lookup request.
    :raises TypeError: if the reference has neither a UUID nor a name.
    """
    uuid_text = _uuid_text(reference)
    if uuid_text is not None:
        return Request(f"{prefix}_lookup_by_uuid", {"uuid": uuid_text})
    name = reference if isinstance(reference, str) else getattr(reference, "name", None)
    if not isinstance(name, str):
        raise TypeError(f"cannot find a {prefix} by {reference!r}")
    return Request(f"{prefix}_lookup_by_name", {"name": name})


def _uuid_text(reference: object) -> str | None:
    """Return the UUID a reference stands for, if it has one.

    :param reference: a ``UUID``, text, or a model.
    :returns: the UUID as text, or ``None`` if the reference is a name.
    """
    if isinstance(reference, UUID):
        return str(reference)
    if isinstance(reference, str) and _UUID_TEXT.fullmatch(reference):
        return reference
    model_uuid = getattr(reference, "uuid", None)
    return model_uuid if isinstance(model_uuid, str) else None
