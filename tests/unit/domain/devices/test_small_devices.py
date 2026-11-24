import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import Devices


def test_filesystem_type_defaults_to_mount() -> None:
    devices = Devices.from_xml(
        "<devices><filesystem><source dir='/a'/><target dir='t'/></filesystem>"
        "<filesystem type='ram'><source usage='1024' units='MiB'/></filesystem>"
        "</devices>"
    )

    assert [type(item).__name__ for item in devices.filesystems] == [
        "MountFilesystem",
        "RamFilesystem",
    ]
    assert devices.filesystems[0].type is None


def test_filesystem_space_limits_keep_their_unit() -> None:
    devices = Devices.from_xml(
        "<devices><filesystem type='ram'><source usage='1'/>"
        "<space_hard_limit unit='GiB'>2</space_hard_limit></filesystem></devices>"
    )

    limit = devices.filesystems[0].space_hard_limit
    assert limit is not None
    assert limit.to_bytes() == 2 * 1024**3


def test_tpm_backend_type_selects_the_variant() -> None:
    devices = Devices.from_xml(
        "<devices><tpm model='tpm-crb'><backend type='emulator' version='2.0'>"
        "<active_pcr_banks><sha1/><sha256/></active_pcr_banks></backend></tpm>"
        "<tpm><backend type='passthrough'><device path='/dev/tpm0'/></backend></tpm>"
        "</devices>"
    )

    assert [tpm.backend.type for tpm in devices.tpms] == ["emulator", "passthrough"]


def test_tpm_rejects_unknown_backend() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><tpm><backend type='crystal-ball'/></tpm></devices>")


def test_rng_random_backend_has_a_path_as_text() -> None:
    devices = Devices.from_xml(
        "<devices><rng model='virtio'><rate bytes='1234' period='2000'/>"
        "<backend model='random'>/dev/random</backend></rng></devices>"
    )

    (rng,) = devices.rngs
    assert rng.backend.value == "/dev/random"
    assert rng.rate is not None
    assert rng.rate.bytes == 1234


def test_rng_builtin_backend_has_no_text() -> None:
    devices = Devices.from_xml(
        "<devices><rng model='virtio'><backend model='builtin'/></rng></devices>"
    )

    assert devices.rngs[0].backend.value is None


def test_watchdog_and_panic() -> None:
    devices = Devices.from_xml(
        "<devices><watchdog model='i6300esb' action='poweroff'/><panic model='hyperv'/>"
        "</devices>"
    )

    assert devices.watchdogs[0].action == "poweroff"
    assert devices.panics[0].model == "hyperv"


def test_memory_device_target_sizes() -> None:
    devices = Devices.from_xml(
        "<devices><memory model='dimm'><target><size unit='MiB'>512</size>"
        "<node>0</node></target></memory></devices>"
    )

    (memory,) = devices.memories
    assert memory.target.size.to_bytes() == 512 * 1024**2
    assert memory.target.node == 0


def test_shmem_requires_a_name() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><shmem/></devices>")


def test_redirdev_with_boot_order() -> None:
    devices = Devices.from_xml(
        "<devices><redirdev bus='usb' type='spicevmc'><boot order='2'/></redirdev>"
        "</devices>"
    )

    assert devices.redirdevs[0].boot is not None
    assert devices.redirdevs[0].boot.order == 2


def test_vsock_cid_auto() -> None:
    devices = Devices.from_xml("<devices><vsock><cid auto='yes'/></vsock></devices>")

    assert devices.vsock is not None
    assert devices.vsock.cid is not None
    assert devices.vsock.cid.auto is True
