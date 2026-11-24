"""The XDR parser on small inputs."""

import pytest

from tools.xdr_parser import (
    Declaration,
    Enum,
    Struct,
    Typedef,
    TypeUse,
    Union,
    XdrSyntaxError,
    parse,
)


def test_constants_may_refer_to_earlier_ones_and_external_names() -> None:
    definitions = parse(
        "const A = 0x10; const B = A; const C = FROM_HEADER;", {"FROM_HEADER": 7}
    )

    assert definitions.constants == {"A": 16, "B": 16, "C": 7}


def test_comments_and_percent_lines_are_dropped() -> None:
    definitions = parse("%#include <x.h>\n/* c */ const A = 1; /* d */", {})

    assert definitions.constants == {"A": 1}


def test_declaration_shapes() -> None:
    definitions = parse(
        "struct s { unsigned hyper a; string b<10>; opaque c[16]; int d<>; t *e; };",
        {},
    )

    struct = definitions.types[0]
    assert isinstance(struct, Struct)
    assert struct.fields == [
        Declaration("a", TypeUse("uhyper")),
        Declaration("b", TypeUse("string", "variable", 10)),
        Declaration("c", TypeUse("opaque", "fixed", 16)),
        Declaration("d", TypeUse("int", "variable", None)),
        Declaration("e", TypeUse("t", "optional")),
    ]


def test_enum_members_without_a_value_count_up() -> None:
    definitions = parse("enum e { A = 5, B, C };", {})

    assert definitions.types == [Enum("e", [("A", 5), ("B", 6), ("C", 7)])]


def test_typedef_and_union() -> None:
    definitions = parse(
        "typedef string name<4>;"
        "union u switch (int kind) { case 1: int i; case 2: void; };",
        {},
    )

    typedef, union = definitions.types
    assert isinstance(typedef, Typedef)
    assert typedef.name == "name"
    assert isinstance(union, Union)
    assert union.arms == [(1, Declaration("i", TypeUse("int"))), (2, None)]


@pytest.mark.parametrize(
    "text", ["const A = ;", "struct s { int a }", "bogus x;", "const A = B;"]
)
def test_bad_input_is_a_syntax_error(text: str) -> None:
    with pytest.raises(XdrSyntaxError):
        parse(text, {})
