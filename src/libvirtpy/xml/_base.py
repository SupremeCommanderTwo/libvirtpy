"""Shared base model and XML serialization defaults."""

from typing import Any, TypeVar, cast

from lxml import etree as lxml_etree
from pydantic import ConfigDict
from pydantic_xml import BaseXmlModel, errors

# pydantic-xml's backend alias: lxml at run time (a required dependency), but
# typed as the standard library's etree, which the overridden methods declare.
from pydantic_xml.element.native import etree

from libvirtpy.xml._xml_element import StableXmlElement

__all__ = ["LibvirtXmlModel"]

ModelT = TypeVar("ModelT", bound="LibvirtXmlModel")


class LibvirtXmlModel(BaseXmlModel, search_mode="unordered"):
    """Base class of every libvirtpy.xml model.

    ``search_mode="unordered"`` matters: libvirt does not guarantee child order,
    and pydantic-xml's default ``strict`` mode silently drops elements that
    appear out of declaration order.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    @classmethod
    def from_xml_tree(
        cls: type[ModelT],
        root: etree.Element,
        # Same as pydantic-xml: a free-form validation context.
        context: dict[str, Any] | None = None,
        empty_as_string: bool = True,
    ) -> ModelT:
        """Parse an element tree, keeping sibling order and empty elements.

        ``empty_as_string`` keeps ``<bootloader/>`` or ``<cmdline></cmdline>``:
        with pydantic-xml's default they read as ``None`` (absent) and are
        lost on a round trip. Models with optional element text use
        ``OptionalText`` to turn ``""`` back into ``None``.

        The tree is read through ``StableXmlElement``, which does not reorder
        same-tag siblings (see ``libvirtpy.xml._xml_element``).

        :param root: the element to read; its tag must be this model's tag.
        :param context: validation context passed to the field validators.
        :param empty_as_string: read an empty element as ``""`` instead of ``None``.
        :returns: the parsed model.
        :raises pydantic_xml.errors.ParsingError: if ``root`` is not the
            element of this model.
        :raises pydantic.ValidationError: if the content does not fit the model.
        """
        serializer = cls.__xml_serializer__
        assert serializer is not None, f"model {cls.__name__} is partially initialized"

        if root.tag != serializer.element_name:
            raise errors.ParsingError(
                f"root element not found (actual: {root.tag}, "
                f"expected: {serializer.element_name})"
            )

        parsed = serializer.deserialize(
            # At run time root is an lxml element (lxml is a required dependency);
            # pydantic-xml annotates it with the standard library's type.
            StableXmlElement.from_native(cast(lxml_etree._Element, root)),
            context=context,
            sourcemap={},
            loc=(),
            empty_as_string=empty_as_string,
        )
        return cast(ModelT, parsed)

    @classmethod
    def from_xml(
        cls: type[ModelT],
        source: str | bytes,
        # Same as pydantic-xml: a free-form validation context.
        context: dict[str, Any] | None = None,
        empty_as_string: bool = True,
        # Forwarded unchanged to etree.fromstring, whose options are untyped.
        **kwargs: Any,
    ) -> ModelT:
        """Parse XML, reading empty elements as ``""`` (see ``from_xml_tree``).

        :param source: the XML document.
        :param context: validation context passed to the field validators.
        :param empty_as_string: read an empty element as ``""`` instead of ``None``.
        :param kwargs: passed to :func:`lxml.etree.fromstring`.
        :returns: the parsed model.
        :raises pydantic.ValidationError: if the content does not fit the model.
        """
        return super().from_xml(
            source, context=context, empty_as_string=empty_as_string, **kwargs
        )

    def to_xml_tree(
        self,
        *,
        skip_empty: bool = False,
        exclude_none: bool = True,
        exclude_unset: bool = False,
    ) -> etree.Element:
        """Serialize to an lxml element, leaving out fields that are ``None``.

        ``exclude_none`` is used instead of ``skip_empty``: ``skip_empty`` also
        drops empty elements such as ``<acpi/>`` and empty attribute values.

        :param skip_empty: drop empty elements and attributes; leave it off.
        :param exclude_none: leave out fields that are ``None``.
        :param exclude_unset: leave out fields that were never set.
        :returns: the root element.
        """
        return super().to_xml_tree(
            skip_empty=skip_empty,
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
        )

    def to_xml(
        self,
        *,
        skip_empty: bool = False,
        exclude_none: bool = True,
        exclude_unset: bool = False,
        # Forwarded unchanged to etree.tostring, whose options are untyped.
        **kwargs: Any,
    ) -> str | bytes:
        """Serialize to XML, leaving out fields that are ``None``.

        :param skip_empty: drop empty elements and attributes; leave it off.
        :param exclude_none: leave out fields that are ``None``.
        :param exclude_unset: leave out fields that were never set.
        :param kwargs: passed to :func:`lxml.etree.tostring`, for example
            ``encoding="unicode"`` to get a ``str``.
        :returns: the XML, as ``bytes`` unless ``encoding="unicode"`` is given.
        """
        return super().to_xml(
            skip_empty=skip_empty,
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            **kwargs,
        )
