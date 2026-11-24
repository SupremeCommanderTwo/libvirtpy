import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import (
    Devices,
    PciController,
    PciControllerModel,
    PciControllerTarget,
    PciHole64,
    UsbController,
    UsbMaster,
    VirtioSerialController,
)


def test_controller_type_selects_the_variant() -> None:
    devices = Devices.from_xml(
        "<devices><controller type='usb' index='0' model='qemu-xhci' ports='15'/>"
        "<controller type='virtio-serial' index='0'/></devices>"
    )

    assert devices.controllers == [
        UsbController(type="usb", index=0, model="qemu-xhci", ports=15),
        VirtioSerialController(type="virtio-serial", index=0),
    ]


def test_controllers_keep_document_order() -> None:
    devices = Devices.from_xml(
        "<devices><controller type='pci' index='0' model='pcie-root'/>"
        "<controller type='usb' index='0'/>"
        "<controller type='pci' index='1' model='pcie-root-port'/></devices>"
    )

    assert [controller.type for controller in devices.controllers] == [
        "pci",
        "usb",
        "pci",
    ]


def test_unknown_controller_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><controller type='firewire'/></devices>")


def test_controller_model_must_match_its_type() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml(
            "<devices><controller type='ide' model='qemu-xhci'/></devices>"
        )


def test_pci_controller_model_attribute_and_element() -> None:
    devices = Devices.from_xml(
        "<devices><controller type='pci' index='1' model='pcie-root-port'>"
        "<model name='pcie-root-port'/><target chassis='1' port='0x10'/>"
        "</controller></devices>"
    )

    assert devices.controllers == [
        PciController(
            type="pci",
            index=1,
            model="pcie-root-port",
            model_info=PciControllerModel(name="pcie-root-port"),
            target=PciControllerTarget(chassis="1", port="0x10"),
        )
    ]


def test_pci_root_pcihole64() -> None:
    controller = PciController(
        type="pci", index=0, model="pci-root", pcihole64=PciHole64(value=1, unit="GiB")
    )

    assert controller.to_xml() == (
        b'<controller index="0" type="pci" model="pci-root">'
        b'<pcihole64 unit="GiB">1</pcihole64></controller>'
    )


def test_usb_companion_controller_master() -> None:
    devices = Devices.from_xml(
        "<devices><controller type='usb' index='0' model='ich9-uhci1'>"
        "<master startport='0'/></controller></devices>"
    )

    assert devices.controllers[0] == UsbController(
        type="usb", index=0, model="ich9-uhci1", master=UsbMaster(startport="0")
    )


def test_unknown_controller_type_before_a_known_one_is_rejected() -> None:
    # A discriminated union would silently drop both controllers here.
    with pytest.raises(ValidationError):
        Devices.from_xml(
            "<devices><controller type='firewire'/><controller type='usb'/></devices>"
        )


def test_controller_without_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><controller index='0'/></devices>")
