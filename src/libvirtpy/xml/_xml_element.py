"""An XML element for pydantic-xml whose "unordered" search keeps sibling order.

pydantic-xml's ``search_mode="unordered"`` consumes a child by *swapping* it to
the front of the unread children. That reorders the others: reading ``<disk>``
first from ``[controller0, controller1, disk]`` leaves ``[disk, controller1,
controller0]``, and the controllers are then read in the wrong order (checked
with pydantic-xml 2.22). Device order matters to libvirt, so this is data
corruption.

``StableXmlElement`` moves the found child to the front *without* disturbing
the rest. ``LibvirtXmlModel.from_xml_tree`` uses it for every parse. This
module depends on pydantic-xml internals; the tests in ``tests/unit/test_base.py``
fail if an upgrade breaks it, or make it unnecessary.
"""

from typing import cast

from lxml import etree
from pydantic_xml.element.element import SearchMode
from pydantic_xml.element.element import XmlElement as BaseXmlElement
from pydantic_xml.element.native.lxml import XmlElement as LxmlXmlElement

__all__ = ["StableXmlElement"]


class StableXmlElement(LxmlXmlElement):
    """An lxml-backed pydantic-xml element with an order-preserving search."""

    __slots__ = ()

    @classmethod
    def from_native(cls, element: etree._Element) -> StableXmlElement:
        """Build the element tree from ``element``, ignoring comments and PIs.

        :param element: the lxml element to copy, with its descendants.
        :returns: the same tree as ``StableXmlElement`` objects.
        """
        return cls(
            tag=str(element.tag),
            text=element.text,
            tail=element.tail,
            attributes={
                str(name): str(value) for name, value in element.attrib.items()
            },
            elements=[
                cls.from_native(child)
                for child in element
                if isinstance(child.tag, str)  # comments and PIs have a function tag
            ],
            sourceline=cast(int, element.sourceline)
            if element.sourceline is not None
            else -1,
        )

    def find_element(
        self,
        tag: str,
        search_mode: SearchMode,
        look_behind: bool = True,
        step_forward: bool = True,
    ) -> BaseXmlElement[etree._Element] | None:
        """Find the next child with ``tag``; "unordered" mode keeps sibling order.

        :param tag: the tag of the child to find.
        :param search_mode: how pydantic-xml searches; only ``UNORDERED`` differs
            from the base class.
        :param look_behind: also accept the child that was read last.
        :param step_forward: mark the child as read.
        :returns: the child, or ``None`` if there is none left.
        """
        if search_mode != SearchMode.UNORDERED:
            return super().find_element(tag, search_mode, look_behind, step_forward)
        return self._stable_search(
            tag, look_behind=look_behind, step_forward=step_forward
        )

    def pop_element(
        self,
        tag: str,
        search_mode: SearchMode,
        remove: bool = False,
    ) -> BaseXmlElement[etree._Element] | None:
        """Find a child like ``find_element`` and optionally detach its content.

        :param tag: the tag of the child to find.
        :param search_mode: how pydantic-xml searches; only ``UNORDERED`` differs
            from the base class.
        :param remove: take the child's text, attributes and children out of it.
        :returns: the child, or ``None`` if there is none left.
        """
        if search_mode != SearchMode.UNORDERED:
            return super().pop_element(tag, search_mode, remove)

        element = self._stable_search(tag, look_behind=False, step_forward=True)
        if element is None or not remove:
            return element

        return type(self)(
            tag=element.tag,
            nsmap=element.nsmap,
            text=element.pop_text(),
            tail=element.pop_tail(),
            attributes=element.pop_attributes(),
            elements=element.pop_elements(),
            sourceline=element.get_sourceline(),
        )

    def _stable_search(
        self, tag: str, *, look_behind: bool, step_forward: bool
    ) -> BaseXmlElement[etree._Element] | None:
        """Find the next unread child with ``tag`` without reordering the others.

        :param tag: the tag of the child to find.
        :param look_behind: also accept the child that was read last.
        :param step_forward: mark the child as read.
        :returns: the child, or ``None`` if there is none left.
        """
        state = self._state
        if look_behind and state.next_element_idx != 0:
            previous = state.elements[state.next_element_idx - 1]
            if previous.tag == tag:
                return previous

        for index in range(state.next_element_idx, len(state.elements)):
            candidate = state.elements[index]
            if candidate.tag != tag:
                continue
            # Unlike pydantic-xml, move the match without reordering the others.
            state.elements.insert(state.next_element_idx, state.elements.pop(index))
            if step_forward:
                state.next_element_idx += 1
            return candidate

        return None
