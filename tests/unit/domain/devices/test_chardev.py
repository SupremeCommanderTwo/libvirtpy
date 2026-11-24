import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import Console, Devices


def test_serial_source_target_and_model() -> None:
    devices = Devices.from_xml(
        "<devices><serial type='tcp'><source mode='bind' host='127.0.0.1' "
        "service='4555'/><protocol type='telnet'/>"
        "<target type='isa-serial' port='0'><model name='isa-serial'/></target>"
        "</serial></devices>"
    )

    (serial,) = devices.serials
    assert serial.type == "tcp"
    assert serial.sources[0].service == "4555"

    assert serial.protocol is not None
    assert serial.protocol.type == "telnet"

    assert serial.target is not None
    assert serial.target.model is not None
    assert serial.target.model.name == "isa-serial"


def test_udp_device_has_two_sources() -> None:
    devices = Devices.from_xml(
        "<devices><serial type='udp'><source mode='bind' host='0.0.0.0' service='1'/>"
        "<source mode='connect' host='1.2.3.4' service='2'/></serial></devices>"
    )

    assert [source.mode for source in devices.serials[0].sources] == ["bind", "connect"]


def test_console_without_type_but_with_tty() -> None:
    devices = Devices.from_xml("<devices><console tty='/dev/pts/5'/></devices>")

    assert devices.consoles == [Console(tty="/dev/pts/5")]


def test_channel_target_is_virtio_with_name() -> None:
    devices = Devices.from_xml(
        "<devices><channel type='unix'><source mode='bind' path='/p'/>"
        "<target type='virtio' name='org.qemu.guest_agent.0' state='connected'/>"
        "</channel></devices>"
    )

    (channel,) = devices.channels
    assert channel.target is not None
    assert channel.target.name == "org.qemu.guest_agent.0"
    assert channel.target.state == "connected"


def test_serial_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        Devices.from_xml("<devices><serial type='smoke-signal'/></devices>")


def test_chardev_log_append_is_on_off() -> None:
    devices = Devices.from_xml(
        "<devices><serial type='pty'><log file='/l' append='on'/></serial></devices>"
    )

    assert devices.serials[0].log is not None
    assert devices.serials[0].log.append is True
