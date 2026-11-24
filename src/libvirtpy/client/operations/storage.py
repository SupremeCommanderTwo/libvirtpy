"""Operations on storage pools and their volumes."""

from libvirtpy.client.operations._common import (
    ACTIVE,
    INACTIVE,
    as_int,
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    one_handle,
)
from libvirtpy.client.references import (
    PoolRef,
    VolumeRef,
    pool_lookup,
    volume_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.storage import Pool, Volume

__all__ = [
    "build_pool",
    "create_pool",
    "create_pool_volume",
    "define_pool",
    "delete_pool",
    "delete_pool_volume",
    "destroy_pool",
    "get_pool_autostart",
    "list_pool_volumes",
    "list_pools",
    "lookup_pool",
    "lookup_pool_volume",
    "refresh_pool",
    "resize_pool_volume",
    "set_pool_autostart",
    "start_pool",
    "undefine_pool",
    "wipe_pool_volume",
]


def lookup_pool(pool: PoolRef) -> Operation[Pool]:
    """Return the configuration of a storage pool.

    :param pool: a name, UUID or ``Pool`` model.
    :returns: the pool.
    :raises NoStoragePoolError: if there is no such pool.
    """
    handle = yield from one_handle(pool_lookup(pool))
    return (yield from fetch_model("storage_pool_get_xml_desc", handle, Pool))


def list_pools(*, active: bool | None = None) -> Operation[list[Pool]]:
    """Return the storage pools.

    :param active: ``True`` for active pools only, ``False`` for the others,
        ``None`` for all.
    :returns: the pools.
    """
    flags = {True: ACTIVE, False: INACTIVE, None: 0}[active]
    handles = yield from many_handles(
        Request("connect_list_all_storage_pools", {"need_results": 1, "flags": flags})
    )
    return (yield from fetch_models("storage_pool_get_xml_desc", handles, Pool))


def define_pool(pool: Pool | str, *, flags: int = 0) -> Operation[Pool]:
    """Define (or redefine) a persistent storage pool without starting it.

    :param pool: the configuration, as a model or XML text.
    :param flags: ``virStoragePoolDefineFlags``.
    :returns: the stored configuration, with what libvirt filled in.
    """
    xml = as_xml(pool)
    handle = yield from one_handle(
        Request("storage_pool_define_xml", {"xml": xml, "flags": flags})
    )
    return (yield from fetch_model("storage_pool_get_xml_desc", handle, Pool))


def create_pool(pool: Pool | str, *, flags: int = 0) -> Operation[Pool]:
    """Start a transient storage pool: it disappears when it stops.

    :param pool: the configuration, as a model or XML text.
    :param flags: ``virStoragePoolCreateFlags``.
    :returns: the running pool.
    """
    xml = as_xml(pool)
    handle = yield from one_handle(
        Request("storage_pool_create_xml", {"xml": xml, "flags": flags})
    )
    return (yield from fetch_model("storage_pool_get_xml_desc", handle, Pool))


def undefine_pool(pool: PoolRef) -> Operation[None]:
    """Remove a persistent pool's definition.

    :param pool: the pool.
    :raises OperationInvalidError: if the pool is active.
    """
    handle = yield from one_handle(pool_lookup(pool))
    yield Request("storage_pool_undefine", {"pool": handle})


def build_pool(pool: PoolRef, *, flags: int = 0) -> Operation[None]:
    """Create the storage a pool is made of (a directory, a file system, ...).

    :param pool: the pool.
    :param flags: ``virStoragePoolBuildFlags``.
    """
    handle = yield from one_handle(pool_lookup(pool))
    yield Request("storage_pool_build", {"pool": handle, "flags": flags})


def start_pool(pool: PoolRef, *, flags: int = 0) -> Operation[Pool]:
    """Start a defined storage pool.

    :param pool: the pool.
    :param flags: ``virStoragePoolCreateFlags``.
    :returns: the pool, now active.
    :raises OperationInvalidError: if the pool is already active.
    """
    handle = yield from one_handle(pool_lookup(pool))
    yield Request("storage_pool_create", {"pool": handle, "flags": flags})
    return (yield from fetch_model("storage_pool_get_xml_desc", handle, Pool))


def destroy_pool(pool: PoolRef) -> Operation[None]:
    """Stop a storage pool; its volumes stay.

    :param pool: the pool.
    :raises OperationInvalidError: if the pool is not active.
    """
    handle = yield from one_handle(pool_lookup(pool))
    yield Request("storage_pool_destroy", {"pool": handle})


def delete_pool(pool: PoolRef, *, flags: int = 0) -> Operation[None]:
    """Delete the storage a pool is made of.

    :param pool: the pool.
    :param flags: ``virStoragePoolDeleteFlags``.
    """
    handle = yield from one_handle(pool_lookup(pool))
    yield Request("storage_pool_delete", {"pool": handle, "flags": flags})


def refresh_pool(pool: PoolRef) -> Operation[Pool]:
    """Re-read the volumes and the sizes of an active pool.

    :param pool: the pool.
    :returns: the pool with the new sizes.
    """
    handle = yield from one_handle(pool_lookup(pool))
    yield Request("storage_pool_refresh", {"pool": handle, "flags": 0})
    return (yield from fetch_model("storage_pool_get_xml_desc", handle, Pool))


def get_pool_autostart(pool: PoolRef) -> Operation[bool]:
    """Tell whether a pool starts with the host.

    :param pool: the pool.
    :returns: ``True`` if it starts at boot.
    """
    handle = yield from one_handle(pool_lookup(pool))
    return bool(as_int((yield Request("storage_pool_get_autostart", {"pool": handle}))))


def set_pool_autostart(pool: PoolRef, enabled: bool) -> Operation[None]:
    """Make a pool start (or not) with the host.

    :param pool: the pool.
    :param enabled: ``True`` to start it at boot.
    """
    handle = yield from one_handle(pool_lookup(pool))
    yield Request(
        "storage_pool_set_autostart", {"pool": handle, "autostart": int(enabled)}
    )


def list_pool_volumes(pool: PoolRef) -> Operation[list[Volume]]:
    """Return the volumes of a storage pool.

    :param pool: the pool.
    :returns: the volumes.
    """
    handle = yield from one_handle(pool_lookup(pool))
    arguments = {"pool": handle, "need_results": 1, "flags": 0}
    handles = yield from many_handles(
        Request("storage_pool_list_all_volumes", arguments)
    )
    return (yield from fetch_models("storage_vol_get_xml_desc", handles, Volume))


def lookup_pool_volume(pool: PoolRef, volume: VolumeRef) -> Operation[Volume]:
    """Return one volume of a storage pool.

    :param pool: the pool.
    :param volume: a name, a key or an absolute path, or a ``Volume`` model.
    :returns: the volume.
    :raises NoStorageVolumeError: if there is no such volume.
    """
    handle = yield from one_handle(pool_lookup(pool))
    found = yield from one_handle(volume_lookup(handle, volume))
    return (yield from fetch_model("storage_vol_get_xml_desc", found, Volume))


def create_pool_volume(
    pool: PoolRef, volume: Volume | str, *, flags: int = 0
) -> Operation[Volume]:
    """Create a volume in a storage pool.

    :param pool: the pool.
    :param volume: the volume description, as a model or XML.
    :param flags: ``virStorageVolCreateFlags``.
    :returns: the volume as the daemon created it (key, path, ...).
    """
    handle = yield from one_handle(pool_lookup(pool))
    arguments = {"pool": handle, "xml": as_xml(volume), "flags": flags}
    created = yield from one_handle(Request("storage_vol_create_xml", arguments))
    return (yield from fetch_model("storage_vol_get_xml_desc", created, Volume))


def delete_pool_volume(
    pool: PoolRef, volume: VolumeRef, *, flags: int = 0
) -> Operation[None]:
    """Delete a volume of a storage pool.

    :param pool: the pool.
    :param volume: a name, a key or an absolute path, or a ``Volume`` model.
    :param flags: ``virStorageVolDeleteFlags``.
    """
    handle = yield from one_handle(pool_lookup(pool))
    found = yield from one_handle(volume_lookup(handle, volume))
    yield Request("storage_vol_delete", {"vol": found, "flags": flags})


def resize_pool_volume(
    pool: PoolRef, volume: VolumeRef, capacity: int, *, flags: int = 0
) -> Operation[Volume]:
    """Change the capacity of a volume.

    :param pool: the pool.
    :param volume: a name, a key or an absolute path, or a ``Volume`` model.
    :param capacity: the new capacity, in bytes.
    :param flags: ``virStorageVolResizeFlags``.
    :returns: the volume with the new capacity.
    """
    handle = yield from one_handle(pool_lookup(pool))
    found = yield from one_handle(volume_lookup(handle, volume))
    yield Request(
        "storage_vol_resize", {"vol": found, "capacity": capacity, "flags": flags}
    )
    return (yield from fetch_model("storage_vol_get_xml_desc", found, Volume))


def wipe_pool_volume(pool: PoolRef, volume: VolumeRef) -> Operation[None]:
    """Overwrite the data of a volume.

    :param pool: the pool.
    :param volume: a name, a key or an absolute path, or a ``Volume`` model.
    """
    handle = yield from one_handle(pool_lookup(pool))
    found = yield from one_handle(volume_lookup(handle, volume))
    yield Request("storage_vol_wipe", {"vol": found, "flags": 0})
