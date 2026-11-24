import pytest

from tests.helpers.xmlcompare import differences, first_difference


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        pytest.param("<a x='1' y='2'/>", '<a y="2" x="1"/>', id="attribute-order"),
        pytest.param("<a>\n  <b/>\n</a>", "<a><b/></a>", id="whitespace"),
        pytest.param("<a><!-- note --><b/></a>", "<a><b/></a>", id="comment"),
        pytest.param("<a><b/><c/></a>", "<a><c/><b/></a>", id="different-tag-order"),
        pytest.param("<a><b></b></a>", "<a><b/></a>", id="empty-element-form"),
    ],
)
def test_equivalent_documents_have_no_difference(expected: str, actual: str) -> None:
    assert first_difference(expected, actual) is None


@pytest.mark.parametrize(
    ("expected", "actual", "difference"),
    [
        pytest.param(
            "<a><b x='1'/></a>",
            "<a><b x='2'/></a>",
            "/a/b/@x: '1' != '2'",
            id="attribute-value",
        ),
        pytest.param(
            "<a><b x=''/></a>",
            "<a><b/></a>",
            "/a/b/@x: '' != None",
            id="empty-attribute-dropped",
        ),
        pytest.param(
            "<a><b>1</b></a>",
            "<a><b>2</b></a>",
            "/a/b/text(): '1' != '2'",
            id="text",
        ),
        pytest.param(
            "<a><b/><c/></a>", "<a><b/></a>", "/a/c: missing element", id="missing"
        ),
        pytest.param(
            "<a/>", "<a><b/></a>", "/a/b: unexpected element", id="unexpected"
        ),
        pytest.param(
            "<a><d n='1'/><d n='2'/></a>",
            "<a><d n='2'/><d n='1'/></a>",
            "/a/d[1]/@n: '1' != '2'",
            id="same-tag-order",
        ),
        pytest.param(
            "<a><d/><d/></a>", "<a><d/></a>", "/a/d[2]: missing element", id="count"
        ),
    ],
)
def test_differences_report_the_path(
    expected: str, actual: str, difference: str
) -> None:
    assert first_difference(expected, actual) == difference


def test_differences_lists_every_difference_in_document_order() -> None:
    expected = "<a x='1'><b>t</b><c/><d/><d/></a>"
    actual = "<a x='2'><b>u</b><d/><e/></a>"

    assert list(differences(expected, actual)) == [
        "/a/@x: '1' != '2'",
        "/a/b/text(): 't' != 'u'",
        "/a/c: missing element",
        "/a/d[2]: missing element",
        "/a/e: unexpected element",
    ]


def test_missing_element_subtree_is_reported_once() -> None:
    assert list(differences("<a><b><c/><d/></b></a>", "<a/>")) == [
        "/a/b: missing element"
    ]
