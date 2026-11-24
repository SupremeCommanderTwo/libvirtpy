import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import (
    BridgeInterface,
    Devices,
    HostdevInterface,
    NetworkInterface,
    NullInterface,
    UdpInterface,
    UserInterface,
)
from tests.helpers.xmlcompare import assert_xml_equal


def test_interface_type_selects_the_variant() -> None:
    interfaces = _interfaces(
        "<interface type='bridge'><source bridge='br0'/></interface>"
        "<interface type='network'><source network='default'/></interface>"
        "<interface type='user'/><interface type='null'/>"
    )

    assert [type(interface) for interface in interfaces] == [
        BridgeInterface,
        NetworkInterface,
        UserInterface,
        NullInterface,
    ]


def test_unknown_interface_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _interfaces("<interface type='carrier-pigeon'/>")


def test_interface_without_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _interfaces("<interface/>")


def test_mac_address_and_model() -> None:
    (interface,) = _interfaces(
        "<interface type='user'><mac address='52:54:00:6b:3c:86'/>"
        "<model type='virtio'/></interface>"
    )

    assert isinstance(interface, UserInterface)
    assert interface.mac is not None
    assert interface.mac.address == "52:54:00:6b:3c:86"
    assert interface.model is not None
    assert interface.model.type == "virtio"


def test_udp_interface_has_a_local_address() -> None:
    (interface,) = _interfaces(
        "<interface type='udp'><source address='230.0.0.1' port='5558'>"
        "<local address='127.0.0.1' port='5559'/></source></interface>"
    )

    assert isinstance(interface, UdpInterface)
    assert interface.source is not None
    assert interface.source.local is not None
    assert interface.source.local.port == 5559


def test_hostdev_interface_source_is_a_pci_or_usb_address() -> None:
    (interface,) = _interfaces(
        "<interface type='hostdev' managed='yes'><source>"
        "<address type='pci' domain='0x0000' bus='0x04' slot='0x10' function='0x1'/>"
        "</source></interface>"
    )

    assert isinstance(interface, HostdevInterface)
    assert interface.managed is True
    assert interface.source is not None
    assert interface.source.address is not None
    assert interface.source.address.type == "pci"


def test_driver_offloads_are_on_off() -> None:
    (interface,) = _interfaces(
        "<interface type='user'><driver name='vhost' queues='4'>"
        "<host csum='off'/><guest tso4='on'/></driver></interface>"
    )

    assert isinstance(interface, UserInterface)
    assert interface.driver is not None
    assert interface.driver.queues == 4
    assert interface.driver.host is not None
    assert interface.driver.host.csum is False


def test_vlan_tags_keep_order() -> None:
    (interface,) = _interfaces(
        "<interface type='user'><vlan><tag id='42' nativeMode='untagged'/>"
        "<tag id='43'/></vlan></interface>"
    )

    assert isinstance(interface, UserInterface)
    assert interface.vlan is not None
    assert [tag.id for tag in interface.vlan.tags] == [42, 43]


def test_interface_serialization_keeps_attribute_values() -> None:
    xml = (
        '<devices><interface type="bridge"><mac address="52:54:00:00:00:01"/>'
        '<source bridge="br0"/><mtu size="9000"/></interface></devices>'
    )

    assert_xml_equal(xml, Devices.from_xml(xml).to_xml())


def _interfaces(xml: str) -> list[object]:
    return list(Devices.from_xml(f"<devices>{xml}</devices>").interfaces)
