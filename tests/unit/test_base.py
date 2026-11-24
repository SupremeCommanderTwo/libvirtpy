import pytest
from pydantic import ValidationError
from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel


class Item(LibvirtXmlModel, tag="item"):
    name: str = element(tag="name")
    label: str | None = attr(name="label", default=None)
    parts: list[str] = element(tag="part", default_factory=list)


def test_none_attribute_is_left_out() -> None:
    assert Item(name="a").to_xml() == b"<item><name>a</name></item>"


def test_empty_attribute_is_kept() -> None:
    assert Item(name="a", label="").to_xml() == b'<item label=""><name>a</name></item>'


def test_children_are_found_in_any_order() -> None:
    item = Item.from_xml("<item><part>1</part><name>a</name><part>2</part></item>")

    assert item.name == "a"
    assert item.parts == ["1", "2"]


def test_unknown_children_and_attributes_are_ignored() -> None:
    item = Item.from_xml("<item extra='x'><future/><name>a</name></item>")

    assert item.name == "a"


def test_assignment_is_validated() -> None:
    item = Item(name="a")

    with pytest.raises(ValidationError):
        item.parts = "not a list"  # type: ignore[assignment]  # wrong on purpose


class Inventory(LibvirtXmlModel, tag="inventory"):
    # Declared in the opposite order of the document below, on purpose.
    disks: list[str] = element(tag="disk", default_factory=list)
    controllers: list[str] = element(tag="controller", default_factory=list)


def test_same_tag_siblings_keep_their_order_when_other_tags_are_read_first() -> None:
    xml = (
        "<inventory><controller>c0</controller><controller>c1</controller>"
        "<controller>c2</controller><disk>d0</disk><disk>d1</disk></inventory>"
    )

    inventory = Inventory.from_xml(xml)

    assert inventory.controllers == ["c0", "c1", "c2"]
    assert inventory.disks == ["d0", "d1"]


def test_interleaved_same_tag_siblings_keep_their_order() -> None:
    xml = (
        "<inventory><controller>c0</controller><disk>d0</disk>"
        "<controller>c1</controller><disk>d1</disk><controller>c2</controller>"
        "</inventory>"
    )

    inventory = Inventory.from_xml(xml)

    assert inventory.controllers == ["c0", "c1", "c2"]
    assert inventory.disks == ["d0", "d1"]
