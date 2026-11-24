"""The objects of the fake daemon and what every kind of object shares."""

from collections.abc import Callable, Mapping
from uuid import UUID

from libvirtpy.client.testing._common import (
    Arguments,
    ModelT,
    _ensure_uuid,
    _Entry,
    _handle_argument,
    _handle_of,
    _int,
    _key_of,
    _redefine,
)
from libvirtpy.client.transport import Handle
from libvirtpy.rpc.errors import (
    ErrorNumber,
    ExistsError,
    LibvirtError,
    NoDomainError,
    NoFilterError,
    NoInterfaceError,
    NoNetworkError,
    NoNodeDeviceError,
    NoSecretError,
    NoSnapshotError,
    NoStoragePoolError,
    NoStorageVolumeError,
    OperationInvalidError,
)
from libvirtpy.xml.domain import Domain
from libvirtpy.xml.interface import HostInterface
from libvirtpy.xml.network import Network
from libvirtpy.xml.nodedev import Device
from libvirtpy.xml.nwfilter import Filter
from libvirtpy.xml.secret import Secret
from libvirtpy.xml.snapshot import Snapshot
from libvirtpy.xml.storage import Pool, Volume


class FakeState:
    """The objects of the fake daemon and what every kind of object shares."""

    def __init__(self) -> None:
        """Create the state: no domains and no other objects."""
        self._next_domain_id = 1
        self._domains: dict[str, _Entry[Domain]] = {}
        self._networks: dict[str, _Entry[Network]] = {}
        self._pools: dict[str, _Entry[Pool]] = {}
        self._volumes: dict[tuple[str, str], Volume] = {}
        self._secrets: dict[str, _Entry[Secret]] = {}
        self._filters: dict[str, _Entry[Filter]] = {}
        self._interfaces: dict[str, _Entry[HostInterface]] = {}
        self._devices: dict[str, Device] = {}
        self._snapshots: dict[tuple[str, str], Snapshot] = {}
        self._snapshot_count = 0

    def _define(
        self,
        entries: dict[str, _Entry[ModelT]],
        model_type: type[ModelT],
        xml: str,
    ) -> Handle:
        model = model_type.from_xml(xml)
        _ensure_uuid(model)
        key = _key_of(model)
        existing = entries.get(key)
        entries[key] = _Entry(model) if existing is None else _redefine(existing, model)
        return _handle_of(model)

    def _create_transient(
        self,
        entries: dict[str, _Entry[ModelT]],
        model_type: type[ModelT],
        xml: str,
    ) -> Handle:
        model = model_type.from_xml(xml)
        _ensure_uuid(model)
        key = _key_of(model)
        if key in entries:
            raise ExistsError(f"{key} already exists", code=ErrorNumber.DOM_EXIST)
        entries[key] = _Entry(model, active=True, transient=True)
        return _handle_of(model)

    def _undefine(
        self,
        entries: dict[str, _Entry[ModelT]],
        arguments: Arguments,
        not_found: Callable[[str], LibvirtError],
        *,
        check_active: bool = True,
    ) -> None:
        entry = self._get(entries, arguments, not_found)
        if check_active and entry.active:
            raise OperationInvalidError(
                "cannot undefine an active object", code=ErrorNumber.OPERATION_INVALID
            )
        del entries[_key_of(entry.model)]

    def _start(
        self,
        entries: dict[str, _Entry[ModelT]],
        arguments: Arguments,
        not_found: Callable[[str], LibvirtError],
    ) -> None:
        entry = self._get(entries, arguments, not_found)
        if entry.active:
            raise OperationInvalidError(
                "the object is already active", code=ErrorNumber.OPERATION_INVALID
            )
        entry.active = True

    def _stop(
        self,
        entries: dict[str, _Entry[ModelT]],
        arguments: Arguments,
        not_found: Callable[[str], LibvirtError],
    ) -> None:
        entry = self._get(entries, arguments, not_found)
        if not entry.active:
            raise OperationInvalidError(
                "the object is not active", code=ErrorNumber.OPERATION_INVALID
            )
        entry.active = False
        if entry.transient:
            del entries[_key_of(entry.model)]

    def _set_autostart(
        self,
        entries: dict[str, _Entry[ModelT]],
        arguments: Arguments,
        not_found: Callable[[str], LibvirtError],
    ) -> None:
        self._get(entries, arguments, not_found).autostart = bool(
            _int(arguments, "autostart")
        )

    def _list(
        self,
        entries: Mapping[str, _Entry[ModelT]],
        arguments: Arguments,
        inactive_is_one: bool,
    ) -> list[Handle]:
        flags = _int(arguments, "flags")
        active_flag, inactive_flag = (2, 1) if inactive_is_one else (1, 2)
        wanted = [
            entry
            for entry in entries.values()
            if flags == 0
            or (flags & active_flag and entry.active)
            or (flags & inactive_flag and not entry.active)
        ]
        return [_handle_of(entry.model) for entry in wanted]

    def _get(
        self,
        entries: Mapping[str, _Entry[ModelT]],
        arguments: Arguments,
        not_found: Callable[[str], LibvirtError],
    ) -> _Entry[ModelT]:
        handle = _handle_argument(arguments)
        key = handle.uuid if handle.uuid in entries else handle.name
        entry = entries.get(key or "")
        if entry is None:
            raise not_found(handle.name)
        return entry

    def _find_by_name(
        self,
        entries: Mapping[str, _Entry[ModelT]],
        name: str,
        not_found: Callable[[str], LibvirtError],
    ) -> Handle:
        for entry in entries.values():
            if getattr(entry.model, "name", None) == name:
                return _handle_of(entry.model)
        raise not_found(name)

    def _find_by_uuid(
        self,
        entries: Mapping[str, _Entry[ModelT]],
        uuid_text: str,
        not_found: Callable[[str], LibvirtError],
    ) -> Handle:
        wanted = UUID(uuid_text)
        for entry in entries.values():
            model_uuid = getattr(entry.model, "uuid", None)
            if model_uuid is not None and UUID(model_uuid) == wanted:
                return _handle_of(entry.model)
        raise not_found(uuid_text)

    def _no_domain(self, what: str) -> LibvirtError:
        return NoDomainError(
            f"Domain not found: no domain with matching name '{what}'",
            code=ErrorNumber.NO_DOMAIN,
        )

    def _no_network(self, what: str) -> LibvirtError:
        return NoNetworkError(
            f"Network not found: no network with matching name '{what}'",
            code=ErrorNumber.NO_NETWORK,
        )

    def _no_pool(self, what: str) -> LibvirtError:
        return NoStoragePoolError(
            f"Storage pool not found: no pool with matching name '{what}'",
            code=ErrorNumber.NO_STORAGE_POOL,
        )

    def _no_volume(self, what: str) -> LibvirtError:
        return NoStorageVolumeError(
            f"Storage volume not found: no volume with matching name '{what}'",
            code=ErrorNumber.NO_STORAGE_VOL,
        )

    def _no_secret(self, what: str) -> LibvirtError:
        return NoSecretError(
            f"Secret not found: no secret with matching uuid '{what}'",
            code=ErrorNumber.NO_SECRET,
        )

    def _no_filter(self, what: str) -> LibvirtError:
        return NoFilterError(
            f"Network filter not found: no nwfilter with matching name '{what}'",
            code=ErrorNumber.NO_NWFILTER,
        )

    def _no_interface(self, what: str) -> LibvirtError:
        return NoInterfaceError(
            f"Interface not found: no interface with matching name '{what}'",
            code=ErrorNumber.NO_INTERFACE,
        )

    def _no_device(self, what: str) -> LibvirtError:
        return NoNodeDeviceError(
            f"Node device not found: no device with matching name '{what}'",
            code=ErrorNumber.NO_NODE_DEVICE,
        )

    def _no_snapshot(self, what: str) -> LibvirtError:
        return NoSnapshotError(
            f"Domain snapshot not found: no snapshot with matching name '{what}'",
            code=ErrorNumber.NO_DOMAIN_SNAPSHOT,
        )
