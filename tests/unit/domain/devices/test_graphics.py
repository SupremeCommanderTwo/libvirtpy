import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import (
    AddressListen,
    Devices,
    NetworkListen,
    SpiceGraphics,
    VncGraphics,
)


def test_graphics_type_selects_the_variant() -> None:
    graphics = _graphics("<graphics type='vnc'/><graphics type='spice'/>")

    assert [type(item) for item in graphics] == [VncGraphics, SpiceGraphics]


def test_unknown_graphics_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _graphics("<graphics type='hologram'/>")


def test_vnc_port_may_be_minus_one() -> None:
    (vnc,) = _graphics("<graphics type='vnc' port='-1' autoport='yes'/>")

    assert isinstance(vnc, VncGraphics)
    assert vnc.port == -1
    assert vnc.autoport is True


def test_listen_type_selects_the_variant() -> None:
    (vnc,) = _graphics(
        "<graphics type='vnc'><listen type='address' address='0.0.0.0'/>"
        "<listen type='network' network='n' address='10.0.0.1'/></graphics>"
    )

    assert isinstance(vnc, VncGraphics)
    assert vnc.listens == [
        AddressListen(type="address", address="0.0.0.0"),
        NetworkListen(type="network", network="n", address="10.0.0.1"),
    ]


def test_spice_channels_and_compression() -> None:
    (spice,) = _graphics(
        "<graphics type='spice'><channel name='main' mode='secure'/>"
        "<channel name='inputs' mode='insecure'/><image compression='off'/></graphics>"
    )

    assert isinstance(spice, SpiceGraphics)
    assert [(c.name, c.mode) for c in spice.channels] == [
        ("main", "secure"),
        ("inputs", "insecure"),
    ]
    assert spice.image is not None
    assert spice.image.compression == "off"


def _graphics(xml: str) -> list[object]:
    return list(Devices.from_xml(f"<devices>{xml}</devices>").graphics)
