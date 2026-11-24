import pytest
from pydantic import ValidationError

from libvirtpy.xml.storage import Pool, Volume


def test_pool_type_must_be_known() -> None:
    with pytest.raises(ValidationError):
        Pool.from_xml("<pool type='tape-library'><name>x</name></pool>")


def test_dir_pool_target_permissions() -> None:
    pool = Pool.from_xml(
        "<pool type='dir'><name>p</name><target><path>/images</path><permissions>"
        "<mode>0755</mode><owner>-1</owner><group>0744</group></permissions>"
        "</target></pool>"
    )

    assert pool.target is not None
    assert pool.target.permissions is not None
    assert pool.target.permissions.mode == "0755"
    assert pool.target.permissions.owner == "-1"
    assert pool.target.permissions.group == "0744"


def test_permissions_owner_must_be_a_number() -> None:
    with pytest.raises(ValidationError):
        Pool.from_xml(
            "<pool type='dir'><name>p</name><target><permissions><owner>root</owner>"
            "</permissions></target></pool>"
        )


def test_pool_capacity_keeps_its_unit() -> None:
    pool = Pool.from_xml(
        "<pool type='dir'><name>p</name><capacity unit='GiB'>2</capacity></pool>"
    )

    assert pool.capacity is not None
    assert pool.capacity.to_bytes() == 2 * 1024**3
    assert pool.capacity.unit == "GiB"


def test_network_pool_hosts_keep_order() -> None:
    pool = Pool.from_xml(
        "<pool type='rbd'><name>p</name><source><name>rbd</name>"
        "<host name='b' port='1'/><host name='a'/></source></pool>"
    )

    assert pool.source is not None
    assert [host.name for host in pool.source.hosts] == ["b", "a"]
    assert pool.source.names == ["rbd"]


def test_pool_namespaced_mount_options() -> None:
    pool = Pool.from_xml(
        "<pool type='fs' xmlns:fs='http://libvirt.org/schemas/storagepool/fs/1.0'>"
        "<name>p</name><fs:mount_opts><fs:option name='ro'/></fs:mount_opts></pool>"
    )

    assert pool.mount_options is not None
    assert pool.mount_options.options[0].name == "ro"


def test_volume_target_and_backing_store() -> None:
    volume = Volume.from_xml(
        "<volume><name>v</name><target><path>/v.qcow2</path>"
        "<format type='qcow2'/><nocow/></target>"
        "<backingStore><path>/base</path></backingStore></volume>"
    )

    assert volume.target is not None
    assert volume.target.format is not None
    assert volume.target.format.type == "qcow2"
    assert volume.target.nocow is not None

    assert volume.backing_store is not None
    assert volume.backing_store.path == "/base"


def test_volume_without_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Volume.from_xml("<volume/>")
