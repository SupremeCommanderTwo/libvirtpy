import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import (
    Devices,
    EvdevInput,
    EvdevInputSource,
    HidInput,
    PassthroughInput,
    PassthroughInputSource,
)


def test_input_type_selects_the_variant() -> None:
    devices = Devices.from_xml(
        "<devices><input type='tablet' bus='usb'/>"
        "<input type='passthrough' bus='virtio'>"
        "<source evdev='/dev/input/event1'/></input>"
        "<input type='evdev'><source dev='/dev/input/event2' grab='all' repeat='on'/>"
        "</input></devices>"
    )

    assert devices.inputs == [
        HidInput(type="tablet", bus="usb"),
        PassthroughInput(
            type="passthrough",
            bus="virtio",
            source=PassthroughInputSource(evdev="/dev/input/event1"),
        ),
        EvdevInput(
            type="evdev",
            source=EvdevInputSource(dev="/dev/input/event2", grab="all", repeat=True),
        ),
    ]


def test_passthrough_input_requires_source() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><input type='passthrough' bus='virtio'/></devices>")


def test_mouse_without_bus_keeps_bus_none() -> None:
    devices = Devices.from_xml("<devices><input type='mouse'/></devices>")

    assert devices.inputs == [HidInput(type="mouse")]
