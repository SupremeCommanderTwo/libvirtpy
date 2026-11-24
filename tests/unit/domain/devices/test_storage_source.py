from libvirtpy.xml.domain.devices import Devices
from libvirtpy.xml.domain.storage_source import (
    BlockSource,
    FileDataStore,
    NetworkSource,
    Reservations,
)


def test_data_store_is_a_typed_nested_source() -> None:
    devices = Devices.from_xml(
        "<devices><disk type='network'><source protocol='nbd' name='v'>"
        "<dataStore type='file'><format type='raw'/><source file='/data'/></dataStore>"
        "</source></disk></devices>"
    )

    source = devices.disks[0].source
    assert isinstance(source, NetworkSource)
    assert isinstance(source.data_store, FileDataStore)
    assert source.data_store.format_info is not None
    assert source.data_store.format_info.type == "raw"


def test_block_source_reservations_with_helper_socket() -> None:
    devices = Devices.from_xml(
        "<devices><disk type='block' device='lun'><source dev='/dev/sdb'>"
        "<reservations managed='no' migration='yes'>"
        "<source type='unix' path='/h.sock' mode='client'/></reservations>"
        "</source></disk></devices>"
    )

    source = devices.disks[0].source
    assert isinstance(source, BlockSource)
    assert isinstance(source.reservations, Reservations)

    assert source.reservations.managed is False
    assert source.reservations.source is not None
    assert source.reservations.source.mode == "client"


def test_source_slices_keep_order() -> None:
    devices = Devices.from_xml(
        "<devices><disk type='block'><source dev='/d'><slices>"
        "<slice type='storage' offset='0' size='10'/>"
        "<slice type='storage' offset='20' size='30'/>"
        "</slices></source></disk></devices>"
    )

    source = devices.disks[0].source
    assert isinstance(source, BlockSource)
    assert source.slices is not None
    assert [(s.offset, s.size) for s in source.slices.slices] == [(0, 10), (20, 30)]


def test_mirror_of_a_file_copy() -> None:
    devices = Devices.from_xml(
        "<devices><disk><mirror type='file' file='/c.img' format='qcow2' job='copy' "
        "ready='abort'><format type='qcow2'/><source file='/c.img'/></mirror>"
        "</disk></devices>"
    )

    mirror = devices.disks[0].mirror
    assert mirror is not None
    assert (mirror.job, mirror.ready, mirror.file) == ("copy", "abort", "/c.img")
