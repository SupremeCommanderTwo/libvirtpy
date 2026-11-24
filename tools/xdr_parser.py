"""A parser for the subset of XDR (RFC 4506) that libvirt's ``.x`` files use.

It reads constants, typedefs, enums, structs and unions. ``program`` blocks,
``%`` pass-through lines and comments are dropped. Names that the files take
from C headers (``VIR_UUID_BUFLEN``) come from the ``external`` mapping.
"""

import re
from dataclasses import dataclass, field

__all__ = [
    "Declaration",
    "Definitions",
    "Enum",
    "Struct",
    "TypeUse",
    "Typedef",
    "Union",
    "XdrSyntaxError",
    "parse",
]

BUILTIN_TYPES = {
    "int": "int",
    "short": "int",
    "char": "int",
    "unsigned": "uint",
    "hyper": "hyper",
    "bool": "bool",
    "float": "float",
    "double": "double",
    "string": "string",
    "opaque": "opaque",
}
UNSIGNED_TYPES = {"int": "uint", "short": "uint", "char": "uint", "hyper": "uhyper"}

_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|0[xX][0-9a-fA-F]+|\d+|[{}\[\]<>;:*=,()]")


class XdrSyntaxError(Exception):
    """The text is not XDR this parser understands."""


@dataclass(frozen=True)
class TypeUse:
    """The type of a declaration: a base type and how it is repeated."""

    base: str
    """A builtin (``int``, ``uint``, ``hyper``, ``uhyper``, ``bool``, ``float``,
    ``double``, ``string``, ``opaque``) or the name of a defined type."""
    shape: str = "plain"
    """``plain``, ``optional`` (``T *x``), ``fixed`` (``T x[N]``) or
    ``variable`` (``T x<N>``)."""
    bound: int | None = None
    """``N`` of a fixed or variable shape; ``None`` for ``<>``."""


@dataclass(frozen=True)
class Declaration:
    """A named, typed item: a struct member, a union arm or a typedef."""

    name: str
    type: TypeUse


@dataclass(frozen=True)
class Typedef:
    """``typedef <declaration>;``."""

    declaration: Declaration

    @property
    def name(self) -> str:
        """The name the typedef defines."""
        return self.declaration.name


@dataclass(frozen=True)
class Enum:
    """An enumeration."""

    name: str
    members: list[tuple[str, int]]


@dataclass(frozen=True)
class Struct:
    """A structure."""

    name: str
    fields: list[Declaration]


@dataclass(frozen=True)
class Union:
    """A discriminated union."""

    name: str
    discriminant: Declaration
    arms: list[tuple[int, Declaration | None]]
    """The value of each ``case`` and its declaration (``None`` for ``void``)."""


@dataclass
class Definitions:
    """Everything a file defines, in file order."""

    constants: dict[str, int] = field(default_factory=dict)
    types: list[Typedef | Enum | Struct | Union] = field(default_factory=list)

    def merge(self, other: Definitions) -> None:
        """Add the definitions of another file.

        :param other: the definitions to add.
        """
        self.constants.update(other.constants)
        self.types.extend(other.types)


def parse(text: str, external: dict[str, int]) -> Definitions:
    """Parse the text of a ``.x`` file.

    :param text: the file content.
    :param external: values of names the file takes from C headers.
    :returns: the definitions.
    :raises XdrSyntaxError: on anything unexpected.
    """
    tokens = _tokens(text)
    parser = _Parser(tokens, dict(external))

    while not parser.at_end():
        parser.definition()
    return parser.definitions


class _Parser:
    """A recursive-descent parser over a token list."""

    def __init__(self, tokens: list[str], constants: dict[str, int]) -> None:
        """Create the parser.

        :param tokens: the tokens of the file.
        :param constants: the constants known so far; extended while parsing.
        """
        self._tokens = tokens
        self._position = 0
        self._constants = constants
        self.definitions = Definitions()

    def at_end(self) -> bool:
        """Tell whether every token has been read.

        :returns: ``True`` at the end of the file.
        """
        return self._position >= len(self._tokens)

    def definition(self) -> None:
        """Parse one top-level definition and store it.

        :raises XdrSyntaxError: if the definition is not known.
        """
        keyword = self._next()
        handlers = {
            "const": self._constant,
            "typedef": self._typedef,
            "enum": self._enum,
            "struct": self._struct,
            "union": self._union,
        }
        if keyword not in handlers:
            raise XdrSyntaxError(f"unexpected {keyword!r} at token {self._position}")
        handlers[keyword]()

    def _constant(self) -> None:
        """Parse ``const NAME = value;``."""
        name = self._next()
        self._expect("=")
        value = self._value()
        self._expect(";")

        self._constants[name] = value
        self.definitions.constants[name] = value

    def _typedef(self) -> None:
        """Parse ``typedef <declaration>;``."""
        declaration = self._declaration()
        self._expect(";")
        self.definitions.types.append(Typedef(declaration))

    def _enum(self) -> None:
        """Parse ``enum NAME { ... };``."""
        name = self._next()
        self._expect("{")
        members: list[tuple[str, int]] = []

        while not self._accept("}"):
            member = self._next()
            following = members[-1][1] + 1 if members else 0
            value = self._value() if self._accept("=") else following
            members.append((member, value))

            self._constants[member] = value
            self._accept(",")

        self._expect(";")
        self.definitions.types.append(Enum(name, members))

    def _struct(self) -> None:
        """Parse ``struct NAME { ... };``."""
        name = self._next()
        self._expect("{")
        fields = []

        while not self._accept("}"):
            fields.append(self._declaration())
            self._expect(";")

        self._expect(";")
        self.definitions.types.append(Struct(name, fields))

    def _union(self) -> None:
        """Parse ``union NAME switch (...) { ... };``."""
        name = self._next()
        self._expect("switch")
        self._expect("(")

        discriminant = self._declaration()
        self._expect(")")
        self._expect("{")

        arms: list[tuple[int, Declaration | None]] = []
        while not self._accept("}"):
            self._expect("case")
            label = self._value()
            self._expect(":")
            arms.append((label, self._arm()))

        self._expect(";")
        self.definitions.types.append(Union(name, discriminant, arms))

    def _arm(self) -> Declaration | None:
        """Parse the declaration of one union arm.

        :returns: the declaration, or ``None`` for ``void``.
        """
        if self._accept("void"):
            self._expect(";")
            return None
        declaration = self._declaration()
        self._expect(";")
        return declaration

    def _declaration(self) -> Declaration:
        """Parse ``type [*] name [[N] | <N>]``.

        :returns: the declaration.
        """
        base = self._base_type()
        optional = self._accept("*")
        name = self._next()

        if optional:
            return Declaration(name, TypeUse(base, "optional"))
        if self._accept("["):
            size = self._value()
            self._expect("]")
            return Declaration(name, TypeUse(base, "fixed", size))
        if self._accept("<"):
            limit = None if self._peek() == ">" else self._value()
            self._expect(">")
            return Declaration(name, TypeUse(base, "variable", limit))
        return Declaration(name, TypeUse(base))

    def _base_type(self) -> str:
        """Parse a base type, folding ``unsigned`` into it.

        :returns: the builtin name or the defined type's name.
        """
        word = self._next()
        if word == "unsigned":
            following = self._peek()
            if following in UNSIGNED_TYPES:
                self._next()
                return UNSIGNED_TYPES[following]
            return "uint"
        return BUILTIN_TYPES.get(word, word)

    def _value(self) -> int:
        """Parse a number or the name of a known constant.

        :returns: the value.
        """
        word = self._next()
        if word.isdigit():
            return int(word)
        if word.lower().startswith("0x"):
            return int(word, 16)
        if word in self._constants:
            return self._constants[word]
        raise XdrSyntaxError(f"unknown constant {word!r}")

    def _next(self) -> str:
        """Consume the next token.

        :returns: the token.
        """
        if self.at_end():
            raise XdrSyntaxError("unexpected end of file")
        token = self._tokens[self._position]
        self._position += 1
        return token

    def _peek(self) -> str | None:
        """Look at the next token.

        :returns: the token, or ``None`` at the end.
        """
        if self.at_end():
            return None
        return self._tokens[self._position]

    def _accept(self, token: str) -> bool:
        """Consume the next token if it is ``token``.

        :param token: the token to accept.
        :returns: whether it was consumed.
        """
        if self._peek() != token:
            return False
        self._position += 1
        return True

    def _expect(self, token: str) -> None:
        """Consume the next token, which must be ``token``.

        :param token: the required token.
        """
        found = self._next()
        if found != token:
            raise XdrSyntaxError(f"expected {token!r}, found {found!r}")


def _tokens(text: str) -> list[str]:
    """Split the text into tokens, without comments and ``%`` lines.

    :param text: the file content.
    :returns: the tokens.
    """
    without_comments = _COMMENT.sub(" ", text)
    lines = [line for line in without_comments.splitlines() if line[:1] != "%"]
    return _TOKEN.findall("\n".join(lines))
