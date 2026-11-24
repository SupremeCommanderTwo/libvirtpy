"""Compare two XML documents as normalized trees.

Ignored: whitespace-only text between elements, comments and processing
instructions, attribute order and quoting, and the relative order of children
with *different* tags. Not ignored: the order of same-tag siblings, attribute
values, and any non-whitespace text.

Each difference is a string that starts with a path, such as
``/domain/devices/disk[2]/@bus: 'virtio' != None``.
"""

from collections.abc import Iterator

from lxml import etree

__all__ = ["assert_xml_equal", "differences", "first_difference"]


def differences(expected: str | bytes, actual: str | bytes) -> Iterator[str]:
    """Yield every difference between the documents, in document order.

    A missing or unexpected element is reported once; its subtree is not
    compared further.
    """
    expected_root = _parse(expected)
    actual_root = _parse(actual)
    if expected_root.tag != actual_root.tag:
        yield f"/: root tag {expected_root.tag!r} != {actual_root.tag!r}"
        return
    yield from _compare_elements(expected_root, actual_root, f"/{expected_root.tag}")


def first_difference(expected: str | bytes, actual: str | bytes) -> str | None:
    """Return the first difference, or ``None`` if the documents are equal."""
    return next(differences(expected, actual), None)


def assert_xml_equal(expected: str | bytes, actual: str | bytes) -> None:
    """Fail with the path of the first difference if the documents differ."""
    difference = first_difference(expected, actual)
    assert difference is None, difference


def _parse(document: str | bytes) -> etree._Element:
    parser = etree.XMLParser(
        remove_blank_text=True, remove_comments=True, remove_pis=True
    )
    if isinstance(document, str):
        document = document.encode()
    return etree.fromstring(document, parser)


def _normalized_text(text: str | None) -> str | None:
    if text is None or text.strip() == "":
        return None
    return text


def _compare_elements(
    expected: etree._Element, actual: etree._Element, path: str
) -> Iterator[str]:
    yield from _compare_attributes(expected, actual, path)

    expected_text = _normalized_text(expected.text)
    actual_text = _normalized_text(actual.text)
    if expected_text != actual_text:
        yield f"{path}/text(): {expected_text!r} != {actual_text!r}"

    yield from _compare_children(expected, actual, path)


def _compare_attributes(
    expected: etree._Element, actual: etree._Element, path: str
) -> Iterator[str]:
    expected_attributes = _attributes(expected)
    actual_attributes = _attributes(actual)
    for name in sorted(expected_attributes.keys() | actual_attributes.keys()):
        expected_value = expected_attributes.get(name)
        actual_value = actual_attributes.get(name)
        if expected_value != actual_value:
            yield f"{path}/@{name}: {expected_value!r} != {actual_value!r}"


def _attributes(element: etree._Element) -> dict[str, str]:
    # Parsed documents always have str attributes; lxml-stubs also allow bytes.
    return {str(name): str(value) for name, value in element.attrib.items()}


def _children_by_tag(element: etree._Element) -> dict[str, list[etree._Element]]:
    groups: dict[str, list[etree._Element]] = {}
    for child in element:
        groups.setdefault(str(child.tag), []).append(child)
    return groups


def _compare_children(
    expected: etree._Element, actual: etree._Element, path: str
) -> Iterator[str]:
    expected_groups = _children_by_tag(expected)
    actual_groups = _children_by_tag(actual)
    for tag, expected_children in expected_groups.items():
        actual_children = actual_groups.get(tag, [])
        yield from _compare_siblings(expected_children, actual_children, path, tag)
    for tag in sorted(actual_groups.keys() - expected_groups.keys()):
        yield f"{path}/{tag}: unexpected element"


def _compare_siblings(
    expected_children: list[etree._Element],
    actual_children: list[etree._Element],
    path: str,
    tag: str,
) -> Iterator[str]:
    expected_count = len(expected_children)

    # Not strict: a length mismatch is reported below, after the common prefix.
    pairs = zip(expected_children, actual_children, strict=False)
    for index, (expected_child, actual_child) in enumerate(pairs, start=1):
        child_path = _child_path(path, tag, index, expected_count)
        yield from _compare_elements(expected_child, actual_child, child_path)

    for index in range(len(actual_children) + 1, expected_count + 1):
        yield f"{_child_path(path, tag, index, expected_count)}: missing element"
    for index in range(expected_count + 1, len(actual_children) + 1):
        yield f"{path}/{tag}[{index}]: unexpected element"


def _child_path(path: str, tag: str, index: int, count: int) -> str:
    if count == 1:
        return f"{path}/{tag}"
    return f"{path}/{tag}[{index}]"
