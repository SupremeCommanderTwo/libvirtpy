import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import (
    Devices,
    MdevHostdev,
    PciHostdev,
    ScsiHostdev,
    UsbHostdev,
)


def test_hostdev_type_selects_the_variant() -> None:
    hostdevs = _hostdevs(
        "<hostdev mode='subsystem' type='pci'><source>"
        "<address domain='0x0000' bus='0x06' slot='0x02' function='0x0'/>"
        "</source></hostdev>"
        "<hostdev mode='subsystem' type='usb'><source><vendor id='0x1'/>"
        "<product id='0x2'/></source></hostdev>"
        "<hostdev mode='subsystem' type='mdev' model='vfio-pci'><source>"
        "<address uuid='c7a5fdbd-edaf-9455-926a-d65c16db1809'/></source></hostdev>"
    )

    assert [type(item) for item in hostdevs] == [PciHostdev, UsbHostdev, MdevHostdev]


def test_pci_hostdev_without_source_is_allowed_but_unknown_type_is_not() -> None:
    assert _hostdevs("<hostdev type='pci'/>")
    with pytest.raises(ValidationError):
        _hostdevs("<hostdev type='parallel-universe'/>")


def test_scsi_hostdev_adapter_source() -> None:
    (hostdev,) = _hostdevs(
        "<hostdev mode='subsystem' type='scsi' sgio='filtered'><source>"
        "<adapter name='scsi_host0'/><address bus='0' target='0' unit='0'/>"
        "</source></hostdev>"
    )

    assert isinstance(hostdev, ScsiHostdev)
    assert hostdev.source is not None
    assert hostdev.source.adapter is not None
    assert hostdev.source.adapter.name == "scsi_host0"


def test_hostdev_flags_are_presence_flags() -> None:
    (hostdev,) = _hostdevs("<hostdev type='pci'><readonly/><shareable/></hostdev>")

    assert hostdev.readonly is not None  # type: ignore[attr-defined]
    assert hostdev.shareable is not None  # type: ignore[attr-defined]


def _hostdevs(xml: str) -> list[object]:
    return list(Devices.from_xml(f"<devices>{xml}</devices>").hostdevs)
