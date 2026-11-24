import pytest
from pydantic import ValidationError
from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import OnOff, PresenceFlag, Uuid, YesNo, size_to_bytes


class Switches(LibvirtXmlModel, tag="switches"):
    yes_no: YesNo | None = attr(name="yesno", default=None)
    on_off: OnOff | None = attr(name="onoff", default=None)


class Flags(LibvirtXmlModel, tag="flags"):
    acpi: PresenceFlag | None = element(tag="acpi", default=None)


class Identified(LibvirtXmlModel, tag="identified"):
    uuid: Uuid = element(tag="uuid")


@pytest.mark.parametrize(
    ("xml", "yes_no", "on_off"),
    [
        ("<switches yesno='yes' onoff='on'/>", True, True),
        ("<switches yesno='no' onoff='off'/>", False, False),
        ("<switches/>", None, None),
    ],
)
def test_switches_parse_to_bool_or_none(
    xml: str, yes_no: bool | None, on_off: bool | None
) -> None:
    switches = Switches.from_xml(xml)

    assert switches.yes_no is yes_no
    assert switches.on_off is on_off


def test_switches_serialize_as_words() -> None:
    switches = Switches(yes_no=False, on_off=True)

    assert switches.to_xml() == b'<switches yesno="no" onoff="on"/>'


@pytest.mark.parametrize("value", ["on", "true", "1", "YES", ""])
def test_yes_no_rejects_other_words(value: str) -> None:
    with pytest.raises(ValidationError):
        Switches.from_xml(f"<switches yesno='{value}'/>")


@pytest.mark.parametrize("value", ["yes", "true", "1", "ON"])
def test_on_off_rejects_other_words(value: str) -> None:
    with pytest.raises(ValidationError):
        Switches.from_xml(f"<switches onoff='{value}'/>")


def test_presence_flag_present_parses_to_instance() -> None:
    assert Flags.from_xml("<flags><acpi/></flags>").acpi == PresenceFlag()


def test_presence_flag_absent_parses_to_none() -> None:
    assert Flags.from_xml("<flags/>").acpi is None


def test_presence_flag_serializes_as_empty_element() -> None:
    assert Flags(acpi=PresenceFlag()).to_xml() == b"<flags><acpi/></flags>"


def test_presence_flag_none_is_left_out() -> None:
    assert Flags(acpi=None).to_xml() == b"<flags/>"


def test_presence_flag_can_be_set_by_assignment() -> None:
    flags = Flags()

    flags.acpi = PresenceFlag()

    assert flags.to_xml() == b"<flags><acpi/></flags>"


@pytest.mark.parametrize(
    "uuid",
    ["c7a5fdbd-edaf-9455-926a-d65c16db1809", "C7A5FDBDEDAF9455926AD65C16DB1809"],
)
def test_uuid_is_kept_as_written(uuid: str) -> None:
    xml = f"<identified><uuid>{uuid}</uuid></identified>"

    assert Identified.from_xml(xml).to_xml(encoding="unicode") == xml


@pytest.mark.parametrize("uuid", ["not-a-uuid", "c7a5fdbd-edaf-9455-926a"])
def test_uuid_rejects_malformed_value(uuid: str) -> None:
    with pytest.raises(ValidationError):
        Identified(uuid=uuid)


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (5, "b", 5),
        (5, "bytes", 5),
        (5, "Byte", 5),
        (1, "k", 1024),
        (1, "KiB", 1024),
        (1, "KB", 1000),
        (1, "kb", 1000),
        (2, "M", 2 * 1024**2),
        (2, "MB", 2 * 1000**2),
        (4, "GiB", 4 * 1024**3),
        (1, "TiB", 1024**4),
        (1, "E", 1024**6),
    ],
)
def test_size_to_bytes(value: int, unit: str, expected: int) -> None:
    assert size_to_bytes(value, unit) == expected


@pytest.mark.parametrize("unit", ["", "KiBB", "x", "kbytes", "bytess"])
def test_size_to_bytes_rejects_unknown_unit(unit: str) -> None:
    with pytest.raises(ValueError, match="unknown size unit"):
        size_to_bytes(1, unit)
