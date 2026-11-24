"""Node device models on XML as real daemons produce it."""

from libvirtpy.xml.nodedev import Device


def test_usb_root_hub_without_port_parses() -> None:
    # libvirt 11.6 reports root hubs without <port>, although its schema requires it.
    device = Device.from_xml(
        "<device><name>usb_usb5</name>"
        "<capability type='usb_device'><bus>5</bus><device>1</device>"
        "<product id='0x0002'>2.0 root hub</product>"
        "<vendor id='0x1d6b'>Linux Foundation</vendor></capability></device>"
    )

    capability = device.capabilities[0]

    assert capability.type == "usb_device"
    assert getattr(capability, "port", "missing") is None
