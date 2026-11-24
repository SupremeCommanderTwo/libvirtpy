"""``<metadata>``: arbitrary XML that applications attach to a domain.

libvirt stores it without interpreting it, and it can contain any elements
from any namespace. It is therefore kept as text, one string per child
element, and parsed back when written. Whitespace and comments between the
children are not kept.

Used by ``<domain>``, ``<network>`` and the other documents that allow it.

See https://libvirt.org/formatdomain.html#general-metadata
"""

from lxml import etree
from pydantic_xml import element, xml_field_serializer, xml_field_validator
from pydantic_xml.element.element import XmlElementReader, XmlElementWriter

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._xml_element import StableXmlElement

__all__ = ["Metadata", "RawChildren"]


class RawChildren(LibvirtXmlModel):
    """Base of the elements whose children are arbitrary XML, kept as strings."""

    # The tag is a placeholder: pydantic-xml needs a mapping to build the class,
    # but the hooks below read and write the field themselves.
    elements: list[str] = element(
        tag="metadata-element",
        default_factory=list,
        description="One XML document fragment per child element, in order.",
    )

    @xml_field_validator("elements")
    @classmethod
    def _read_elements(cls, element: XmlElementReader, field_name: str) -> list[str]:
        """Read every child of the element as an XML string.

        :param element: the element being parsed.
        :param field_name: the field this reader fills (``elements``).
        :returns: one string per child, in document order.
        """
        children = element.pop_elements()
        return [
            etree.tostring(child.to_native(), encoding="unicode", with_tail=False)
            for child in children
        ]

    @xml_field_serializer("elements")
    def _write_elements(
        self, element: XmlElementWriter, value: list[str], field_name: str
    ) -> XmlElementWriter:
        """Write each string back as a child element.

        :param element: the element being written.
        :param value: the XML strings to write, in order.
        :param field_name: the field this writer serializes (``elements``).
        :returns: ``element``, with the children appended.
        """
        for text in value:
            parsed = etree.fromstring(text)
            element.append_element(StableXmlElement.from_native(parsed))
        return element


class Metadata(RawChildren, tag="metadata"):
    """``<metadata>``: the application elements, each as an XML string."""
