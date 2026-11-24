import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import (
    BlockDisk,
    Devices,
    DiskTarget,
    FileBackingStore,
    FileDisk,
    NetworkDisk,
    VolumeDisk,
)
from libvirtpy.xml.domain.storage_source import FileSource, NetworkHost, NetworkSource


def test_disk_without_type_is_a_file_disk() -> None:
    devices = Devices.from_xml(
        "<devices><disk device='cdrom'><target dev='sda' bus='sata'/></disk></devices>"
    )

    assert devices.disks == [
        FileDisk(device="cdrom", target=DiskTarget(dev="sda", bus="sata"))
    ]
    assert devices.disks[0].type is None


def test_disk_type_selects_the_variant_and_its_source() -> None:
    devices = Devices.from_xml(
        "<devices><disk type='file'><source file='/a.img'/></disk>"
        "<disk type='block'><source dev='/dev/sdb'/></disk>"
        "<disk type='volume'><source pool='p' volume='v'/></disk></devices>"
    )

    assert [type(disk) for disk in devices.disks] == [FileDisk, BlockDisk, VolumeDisk]
    assert devices.disks[0].source == FileSource(file="/a.img")


def test_unknown_disk_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><disk type='floppy'/></devices>")


def test_disk_source_must_match_the_disk_type() -> None:
    # <source dev=...> is a block source; a file disk ignores the unknown attribute
    # and keeps no device, instead of silently becoming a block disk.
    devices = Devices.from_xml(
        "<devices><disk type='file'><source dev='/dev/sdb'/></disk></devices>"
    )

    assert devices.disks == [FileDisk(type="file", source=FileSource())]


def test_network_disk_keeps_hosts_in_order() -> None:
    devices = Devices.from_xml(
        "<devices><disk type='network'><source protocol='rbd' name='p/i'>"
        "<host name='a' port='1'/><host name='b' port='2'/></source></disk></devices>"
    )

    assert devices.disks == [
        NetworkDisk(
            type="network",
            source=NetworkSource(
                protocol="rbd",
                name="p/i",
                hosts=[NetworkHost(name="a", port=1), NetworkHost(name="b", port=2)],
            ),
        )
    ]


def test_network_disk_rejects_unknown_protocol() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml(
            "<devices><disk type='network'><source protocol='carrier-pigeon'/>"
            "</disk></devices>"
        )


def test_backing_chain_ends_with_an_empty_backing_store() -> None:
    devices = Devices.from_xml(
        "<devices><disk type='file'><source file='/top'/>"
        "<backingStore type='file' index='2'><format type='qcow2'/>"
        "<source file='/base'/><backingStore/></backingStore></disk></devices>"
    )

    chain = devices.disks[0].backing_store
    assert isinstance(chain, FileBackingStore)
    assert chain.index == 2
    assert chain.backing_store == FileBackingStore()


def test_empty_backing_store_round_trips() -> None:
    xml = "<devices><disk><backingStore/></disk></devices>"

    assert Devices.from_xml(xml).to_xml(encoding="unicode") == xml


def test_readonly_and_shareable_are_presence_flags() -> None:
    devices = Devices.from_xml(
        "<devices><disk><readonly/><shareable/></disk></devices>"
    )

    disk = devices.disks[0]
    assert disk.readonly is not None
    assert disk.shareable is not None
    assert disk.transient is None


def test_iotune_values_are_numbers() -> None:
    devices = Devices.from_xml(
        "<devices><disk><iotune><total_bytes_sec>1000</total_bytes_sec>"
        "<read_iops_sec>5</read_iops_sec></iotune></disk></devices>"
    )

    iotune = devices.disks[0].iotune
    assert iotune is not None
    assert (iotune.total_bytes_sec, iotune.read_iops_sec) == (1000, 5)
    assert iotune.write_bytes_sec is None


def test_disk_driver_rejects_unknown_cache_mode() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><disk><driver cache='fast'/></disk></devices>")
