"""Storage pools and volumes."""

from libvirtpy.client.testing._common import (
    Action,
    Arguments,
    _handle_argument,
    _int,
    _pool_name,
    _text,
    _volume_handle,
    _xml_of,
)
from libvirtpy.client.testing._state import FakeState
from libvirtpy.client.transport import Handle
from libvirtpy.rpc.errors import (
    ErrorNumber,
    ExistsError,
    OperationInvalidError,
)
from libvirtpy.xml._shared.storage import Allocation, Capacity
from libvirtpy.xml.storage import Pool, PoolTarget, Volume, VolumeTarget


class StorageActions(FakeState):
    """Storage pools and volumes."""

    def _pool_actions(self) -> dict[str, Action]:
        return {
            "connect_list_all_storage_pools": lambda a: self._list(
                self._pools, a, True
            ),
            "storage_pool_lookup_by_name": lambda a: self._find_by_name(
                self._pools, _text(a, "name"), self._no_pool
            ),
            "storage_pool_lookup_by_uuid": lambda a: self._find_by_uuid(
                self._pools, _text(a, "uuid"), self._no_pool
            ),
            "storage_pool_get_xml_desc": lambda a: _xml_of(
                self._get(self._pools, a, self._no_pool).model
            ),
            "storage_pool_define_xml": self._define_pool,
            "storage_pool_create_xml": self._create_pool,
            "storage_pool_undefine": lambda a: self._undefine(
                self._pools, a, self._no_pool
            ),
            "storage_pool_create": lambda a: self._start(self._pools, a, self._no_pool),
            "storage_pool_destroy": lambda a: self._stop(self._pools, a, self._no_pool),
            "storage_pool_build": lambda _: None,
            "storage_pool_delete": self._delete_pool,
            "storage_pool_refresh": self._refresh_pool,
            "storage_pool_get_autostart": lambda a: int(
                self._get(self._pools, a, self._no_pool).autostart
            ),
            "storage_pool_set_autostart": lambda a: self._set_autostart(
                self._pools, a, self._no_pool
            ),
        }

    def _volume_actions(self) -> dict[str, Action]:
        return {
            "storage_pool_list_all_volumes": self._list_volumes,
            "storage_vol_lookup_by_name": self._lookup_volume_by_name,
            "storage_vol_lookup_by_key": lambda a: self._lookup_volume_by("key", a),
            "storage_vol_lookup_by_path": lambda a: self._lookup_volume_by("path", a),
            "storage_vol_get_xml_desc": lambda a: _xml_of(self._volume(a)),
            "storage_vol_create_xml": self._create_volume,
            "storage_vol_delete": self._delete_volume,
            "storage_vol_resize": self._resize_volume,
            "storage_vol_wipe": lambda a: self._volume(a) and None,
        }

    def _define_pool(self, arguments: Arguments) -> Handle:
        handle = self._define(self._pools, Pool, _text(arguments, "xml"))
        self._complete_pool(self._pools[handle.name].model)
        return handle

    def _create_pool(self, arguments: Arguments) -> Handle:
        handle = self._create_transient(self._pools, Pool, _text(arguments, "xml"))
        self._complete_pool(self._pools[handle.name].model)
        return handle

    def _complete_pool(self, pool: Pool) -> None:
        if pool.target is None:
            pool.target = PoolTarget(path=f"/var/lib/libvirt/images/{pool.name}")
        if pool.capacity is None:
            pool.capacity = Capacity(value=100, unit="GiB")
            pool.allocation = Allocation(value=0, unit="B")

    def _delete_pool(self, arguments: Arguments) -> None:
        entry = self._get(self._pools, arguments, self._no_pool)
        if entry.active:
            raise OperationInvalidError(
                "the pool is active", code=ErrorNumber.OPERATION_INVALID
            )

    def _refresh_pool(self, arguments: Arguments) -> None:
        entry = self._get(self._pools, arguments, self._no_pool)
        if not entry.active:
            raise OperationInvalidError(
                "the pool is not active", code=ErrorNumber.OPERATION_INVALID
            )
        used = sum(
            volume.capacity.to_bytes() if volume.capacity else 0
            for (pool, _), volume in self._volumes.items()
            if pool == entry.model.name
        )
        entry.model.allocation = Allocation(value=used, unit="B")

    def _list_volumes(self, arguments: Arguments) -> list[Handle]:
        pool = self._get(self._pools, arguments, self._no_pool).model.name
        return [
            _volume_handle(volume, owner)
            for (owner, _), volume in self._volumes.items()
            if owner == pool
        ]

    def _lookup_volume_by_name(self, arguments: Arguments) -> Handle:
        pool = self._get(self._pools, {"pool": arguments["pool"]}, self._no_pool)
        volume = self._volumes.get((_pool_name(pool.model), _text(arguments, "name")))
        if volume is None:
            raise self._no_volume(_text(arguments, "name"))
        return _volume_handle(volume, _pool_name(pool.model))

    def _lookup_volume_by(self, field_name: str, arguments: Arguments) -> Handle:
        wanted = _text(arguments, field_name)
        for (pool, _), volume in self._volumes.items():
            target = volume.target.path if volume.target else None
            if (field_name == "key" and volume.key == wanted) or (
                field_name == "path" and target == wanted
            ):
                return _volume_handle(volume, pool)
        raise self._no_volume(wanted)

    def _volume(self, arguments: Arguments) -> Volume:
        handle = _handle_argument(arguments)
        volume = self._volumes.get((handle.parent or "", handle.name))
        if volume is None:
            raise self._no_volume(handle.name)
        return volume

    def _create_volume(self, arguments: Arguments) -> Handle:
        entry = self._get(self._pools, {"pool": arguments["pool"]}, self._no_pool)
        if not entry.active:
            raise OperationInvalidError(
                "the pool is not active", code=ErrorNumber.OPERATION_INVALID
            )
        volume = Volume.from_xml(_text(arguments, "xml"))
        pool_name = _pool_name(entry.model)
        if (pool_name, volume.name) in self._volumes:
            raise ExistsError(
                f"volume {volume.name} exists", code=ErrorNumber.OPERATION_FAILED
            )
        base = (
            entry.model.target.path if entry.model.target else "/var/lib/libvirt/images"
        )
        path = f"{base}/{volume.name}"
        volume.key = path
        volume.target = volume.target or VolumeTarget()
        volume.target.path = path
        volume.allocation = volume.allocation or Allocation(value=0, unit="B")
        self._volumes[(pool_name, volume.name)] = volume
        return _volume_handle(volume, pool_name)

    def _delete_volume(self, arguments: Arguments) -> None:
        handle = _handle_argument(arguments)
        self._volume(arguments)
        del self._volumes[(handle.parent or "", handle.name)]

    def _resize_volume(self, arguments: Arguments) -> None:
        volume = self._volume(arguments)
        volume.capacity = Capacity(value=_int(arguments, "capacity"), unit="B")
