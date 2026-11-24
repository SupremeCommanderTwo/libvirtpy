import pytest
from pydantic import ValidationError
from pydantic_xml import element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml.domain.devices import (
    Address,
    DriveAddress,
    PciAddress,
    UsbAddress,
    VirtioMmioAddress,
    Zpci,
)


class Holder(LibvirtXmlModel, tag="holder"):
    address: Address | None = element(tag="address", default=None)


def test_pci_address_keeps_numbers_as_written() -> None:
    xml = (
        '<holder><address type="pci" domain="0x0000" bus="0x00" slot="0x1f" '
        'function="2" multifunction="on"/></holder>'
    )

    holder = Holder.from_xml(xml)

    assert holder.address == PciAddress(
        type="pci",
        domain="0x0000",
        bus="0x00",
        slot="0x1f",
        function="2",
        multifunction=True,
    )
    assert holder.to_xml(encoding="unicode") == xml


@pytest.mark.parametrize(
    ("xml", "expected"),
    [
        (
            "<address type='drive' controller='0' bus='1' unit='0'/>",
            DriveAddress(type="drive", controller="0", bus="1", unit="0"),
        ),
        (
            "<address type='usb' bus='0' port='1.2'/>",
            UsbAddress(type="usb", bus="0", port="1.2"),
        ),
        ("<address type='virtio-mmio'/>", VirtioMmioAddress(type="virtio-mmio")),
    ],
)
def test_address_type_selects_the_variant(xml: str, expected: Address) -> None:
    assert Holder.from_xml(f"<holder>{xml}</holder>").address == expected


def test_missing_address_is_none_and_not_serialized() -> None:
    holder = Holder.from_xml("<holder/>")

    assert holder.address is None
    assert holder.to_xml() == b"<holder/>"


def test_unknown_address_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Holder.from_xml("<holder><address type='firewire'/></holder>")


def test_pci_address_with_zpci() -> None:
    holder = Holder.from_xml(
        "<holder><address type='pci'><zpci uid='0x0001' fid='0x0'/></address></holder>"
    )

    assert holder.address == PciAddress(type="pci", zpci=Zpci(uid="0x0001", fid="0x0"))


def test_address_number_rejects_non_hex() -> None:
    with pytest.raises(ValidationError):
        PciAddress(type="pci", slot="0xZZ")
