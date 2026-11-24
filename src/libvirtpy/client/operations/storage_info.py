"""Operations that read facts about storage pools and volumes."""

from libvirtpy.client.operations._common import (
    as_bool,
    as_struct,
    as_text,
    as_xml,
    fetch_model,
    on_pool,
    on_volume,
    one_handle,
)
from libvirtpy.client.references import (
    PoolRef,
    VolumeRef,
    pool_lookup,
    volume_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.rpc.protocol import types
from libvirtpy.xml.storage import Pool, Volume

__all__ = [
    "create_pool_volume_from",
    "find_pool_sources",
    "get_pool_info",
    "get_pool_volume_info",
    "get_pool_volume_path",
    "is_pool_active",
    "is_pool_persistent",
    "lookup_pool_by_target_path",
    "lookup_pool_by_volume",
    "wipe_pool_volume_with_pattern",
]


def get_pool_info(pool: PoolRef) -> Operation[types.StoragePoolGetInfoRet]:
    """Return the state and the sizes of a storage pool.

    :param pool: the pool.
    :returns: ``state`` (``virStoragePoolState``) and ``capacity``, ``allocation``
        and ``available`` in bytes.
    """
    reply = yield from on_pool(pool, "storage_pool_get_info")
    return as_struct(reply, types.StoragePoolGetInfoRet)


def is_pool_active(pool: PoolRef) -> Operation[bool]:
    """Tell whether a storage pool is started.

    :param pool: the pool.
    :returns: ``True`` if it is active.
    """
    return as_bool((yield from on_pool(pool, "storage_pool_is_active")))


def is_pool_persistent(pool: PoolRef) -> Operation[bool]:
    """Tell whether a storage pool has a stored configuration.

    :param pool: the pool.
    :returns: ``True`` if persistent, ``False`` if transient.
    """
    return as_bool((yield from on_pool(pool, "storage_pool_is_persistent")))


def lookup_pool_by_target_path(path: str) -> Operation[Pool]:
    """Find the storage pool whose target is a directory.

    :param path: the target path of the pool.
    :returns: the pool.
    :raises NoStoragePoolError: if no pool has that target.
    """
    found = yield from one_handle(
        Request("storage_pool_lookup_by_target_path", {"path": path})
    )
    return (yield from fetch_model("storage_pool_get_xml_desc", found, Pool))


def lookup_pool_by_volume(pool: PoolRef, volume: VolumeRef) -> Operation[Pool]:
    """Find the pool a volume belongs to.

    :param pool: a pool that contains the volume (it is needed to find it).
    :param volume: the volume.
    :returns: the pool of the volume.
    """
    pool_handle = yield from one_handle(pool_lookup(pool))
    volume_handle = yield from one_handle(volume_lookup(pool_handle, volume))
    found = yield from one_handle(
        Request("storage_pool_lookup_by_volume", {"vol": volume_handle})
    )
    return (yield from fetch_model("storage_pool_get_xml_desc", found, Pool))


def get_pool_volume_info(
    pool: PoolRef, volume: VolumeRef, *, flags: int = 0
) -> Operation[types.StorageVolGetInfoFlagsRet]:
    """Return the type and the sizes of a volume.

    :param pool: the pool.
    :param volume: the volume.
    :param flags: ``virStorageVolInfoFlags``: 1 the real size on the host.
    :returns: ``type`` (``virStorageVolType``), ``capacity`` and ``allocation`` in
        bytes.
    """
    reply = yield from on_volume(
        pool, volume, "storage_vol_get_info_flags", flags=flags
    )
    return as_struct(reply, types.StorageVolGetInfoFlagsRet)


def get_pool_volume_path(pool: PoolRef, volume: VolumeRef) -> Operation[str]:
    """Return the path of a volume on the host.

    :param pool: the pool.
    :param volume: the volume.
    :returns: the absolute path.
    """
    return as_text((yield from on_volume(pool, volume, "storage_vol_get_path")))


def create_pool_volume_from(
    pool: PoolRef,
    volume: Volume | str,
    source: VolumeRef,
    *,
    source_pool: PoolRef | None = None,
    flags: int = 0,
) -> Operation[Volume]:
    """Create a volume as a copy of another one.

    :param pool: the pool of the new volume.
    :param volume: the new volume's description, as a model or XML.
    :param source: the volume to copy.
    :param source_pool: the pool of ``source``; ``pool`` if left out.
    :param flags: ``virStorageVolCreateFlags``.
    :returns: the new volume as the daemon created it.
    """
    target = yield from one_handle(pool_lookup(pool))
    origin_pool = yield from one_handle(pool_lookup(source_pool or pool))
    origin = yield from one_handle(volume_lookup(origin_pool, source))

    created = yield from one_handle(
        Request(
            "storage_vol_create_xml_from",
            {
                "pool": target,
                "xml": as_xml(volume),
                "clonevol": origin,
                "flags": flags,
            },
        )
    )
    return (yield from fetch_model("storage_vol_get_xml_desc", created, Volume))


def wipe_pool_volume_with_pattern(
    pool: PoolRef, volume: VolumeRef, algorithm: int, *, flags: int = 0
) -> Operation[None]:
    """Overwrite a volume with a pattern.

    :param pool: the pool.
    :param volume: the volume.
    :param algorithm: ``virStorageVolWipeAlgorithm``: 0 zero, 1 NNSA, 2 DoD,
        3 BSI, 4 Gutmann, 5 Schneier, 6 Pfitzner (7 passes), 7 Pfitzner (33),
        8 random, 9 trim.
    :param flags: reserved, 0.
    """
    yield from on_volume(
        pool, volume, "storage_vol_wipe_pattern", algorithm=algorithm, flags=flags
    )


def find_pool_sources(
    pool_type: str, spec: str | None = None, *, flags: int = 0
) -> Operation[str]:
    """Discover possible sources for a new storage pool (for example NFS exports).

    :param pool_type: the pool type (``netfs``, ``logical``, ``iscsi``, ...).
    :param spec: the source description as XML (``<source><host
        name=.../></source>``).
    :param flags: reserved, 0.
    :returns: the sources found, as ``<sources>`` XML.
    """
    reply = yield Request(
        "connect_find_storage_pool_sources",
        {"type": pool_type, "src_spec": spec, "flags": flags},
    )
    return as_text(reply)
