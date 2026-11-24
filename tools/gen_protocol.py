"""Generate ``libvirtpy/rpc/protocol`` from libvirt's XDR definitions.

Reads ``remote_protocol.x``, ``virnetprotocol.x`` and ``virkeepaliveprotocol.x``
from the pinned corpus (``tools/fetch_samples.py``) and writes:

- ``protocol/types.py``: the constants, enums, and one dataclass per struct or
  union, each with the XDR layout the codec ``xdr.py`` needs;
- ``protocol/procedures.py``: one ``Procedure`` per remote procedure, with its
  argument and return types and the daemon that serves it.

Usage: ``python tools/gen_protocol.py [--check]``; ``--check`` only reports drift.
"""

import argparse
import keyword
import re
import subprocess
import sys
from pathlib import Path

from tools.xdr_parser import (
    Definitions,
    Enum,
    Struct,
    Typedef,
    TypeUse,
    Union,
    parse,
)

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CORPUS = REPOSITORY_ROOT / ".cache" / "libvirt"
OUTPUT = REPOSITORY_ROOT / "src" / "libvirtpy" / "rpc" / "protocol"
SOURCES = (
    CORPUS / "src" / "rpc" / "virnetprotocol.x",
    CORPUS / "src" / "rpc" / "virkeepaliveprotocol.x",
    CORPUS / "src" / "remote" / "remote_protocol.x",
)
GENDISPATCH = CORPUS / "src" / "rpc" / "gendispatch.pl"

# Values that the .x files take from libvirt's C headers. The typed parameter
# enum lives in a header generated at build time; its values are ABI ("must
# remain binary compatible", says remote_protocol.x). The buffer sizes are
# checked against include/libvirt/libvirt-host.h by ``_header_constants``.
TYPED_PARAMETER_TYPES = {
    "VIR_TYPED_PARAM_INT": 1,
    "VIR_TYPED_PARAM_UINT": 2,
    "VIR_TYPED_PARAM_LLONG": 3,
    "VIR_TYPED_PARAM_ULLONG": 4,
    "VIR_TYPED_PARAM_DOUBLE": 5,
    "VIR_TYPED_PARAM_BOOLEAN": 6,
    "VIR_TYPED_PARAM_STRING": 7,
}
HEADER_CONSTANTS = (
    "VIR_UUID_BUFLEN",
    "VIR_SECURITY_MODEL_BUFLEN",
    "VIR_SECURITY_LABEL_BUFLEN",
    "VIR_SECURITY_DOI_BUFLEN",
)
PROCEDURE_ENUM = "remote_procedure"
PROCEDURE_PREFIX = "REMOTE_PROC_"

SIMPLE_TYPES = {
    "int": ("INT", "int"),
    "uint": ("UINT", "int"),
    "hyper": ("HYPER", "int"),
    "uhyper": ("UHYPER", "int"),
    "bool": ("BOOL", "bool"),
    "float": ("FLOAT", "float"),
    "double": ("DOUBLE", "float"),
}


class Generator:
    """Turns parsed definitions into the text of the two generated modules."""

    def __init__(self, definitions: Definitions) -> None:
        """Index the definitions.

        :param definitions: everything the ``.x`` files define.
        """
        self.definitions = definitions
        self.by_name = {item.name: item for item in definitions.types}
        self.class_names = {
            item.name: _class_name(item.name)
            for item in definitions.types
            if isinstance(item, Enum | Struct | Union) and item.name != PROCEDURE_ENUM
        }
        self._check_unique_class_names()

    def types_module(self) -> str:
        """Build ``protocol/types.py``.

        :returns: the unformatted source.
        """
        blocks = [self._constants()]
        for item in self.definitions.types:
            if item.name not in self.class_names:
                continue
            blocks.append(self._definition(item))
        return "\n\n\n".join(blocks)

    def procedures_module(self, drivers: dict[str, str]) -> str:
        """Build ``protocol/procedures.py``.

        :param drivers: the daemon of each procedure name.
        :returns: the unformatted source.
        """
        procedure_enum = self.by_name[PROCEDURE_ENUM]
        assert isinstance(procedure_enum, Enum)

        lines = []
        names = []

        for member, number in procedure_enum.members:
            name = member.removeprefix(PROCEDURE_PREFIX).lower()
            names.append(name.upper())
            lines.append(self._procedure(name, number, drivers[name]))

        table = "_ALL: tuple[Procedure[Any, Any], ...] = (\n"
        table += "".join(f"    {name},\n" for name in names) + ")\n\n"
        table += (
            "PROCEDURES: Final = {procedure.number: procedure for procedure in _ALL}"
        )
        return "\n\n".join([*lines, table])

    def procedure_names(self) -> list[str]:
        """List the procedure names, lower case, in number order.

        :returns: names such as ``domain_lookup_by_name``.
        """
        procedure_enum = self.by_name[PROCEDURE_ENUM]
        assert isinstance(procedure_enum, Enum)
        return [
            member.removeprefix(PROCEDURE_PREFIX).lower()
            for member, _ in procedure_enum.members
        ]

    def member_types(self, struct_name: str) -> list[str]:
        """List the declared type names of a struct's members.

        :param struct_name: the XDR name of the struct.
        :returns: the type text of each member, as written in the file.
        """
        struct = self.by_name.get(struct_name)
        if not isinstance(struct, Struct):
            return []
        return [field.type.base for field in struct.fields]

    # the types file

    def _constants(self) -> str:
        """Write the module-level constants.

        :returns: the source lines.
        """
        lines = [
            f"{name}: Final = {value}"
            for name, value in self.definitions.constants.items()
        ]
        return "\n".join(lines)

    def _definition(self, item: Typedef | Enum | Struct | Union) -> str:
        """Write the class of one definition.

        :param item: the enum, struct or union.
        :returns: the class source.
        """
        if isinstance(item, Enum):
            return self._enum(item)
        if isinstance(item, Struct):
            return self._struct(item)
        if isinstance(item, Union):
            return self._union(item)
        raise TypeError(item)

    def _enum(self, enum: Enum) -> str:
        """Write an ``IntEnum``.

        :param enum: the XDR enum.
        :returns: the class source.
        """
        prefix = _common_prefix([name for name, _ in enum.members])
        lines = [
            f"class {self.class_names[enum.name]}(IntEnum):",
            f'    """XDR enum ``{enum.name}``."""',
            "",
        ]
        for name, value in enum.members:
            lines.append(f"    {_member_name(name, prefix)} = {value}")
        return "\n".join(lines)

    def _struct(self, struct: Struct) -> str:
        """Write a dataclass with its XDR layout.

        :param struct: the XDR struct.
        :returns: the class source.
        """
        class_name = self.class_names[struct.name]
        lines = [
            "@dataclass",
            f"class {class_name}:",
            f'    """XDR struct ``{struct.name}``."""',
            "",
        ]
        table = []

        for declaration in struct.fields:
            attribute = _attribute_name(declaration.name)
            lines.append(f"    {attribute}: {self._annotation(declaration.type)}")
            table.append(f'("{attribute}", {self._descriptor(declaration.type)})')

        lines.append("")
        lines.append(
            "    xdr_fields: ClassVar[tuple[tuple[str, XdrType], ...]] = ("
            + "".join(f"{entry}, " for entry in table)
            + ")"
        )
        return "\n".join(lines)

    def _union(self, union: Union) -> str:
        """Write a dataclass for a union with its arms.

        :param union: the XDR union.
        :returns: the class source.
        """
        class_name = self.class_names[union.name]
        name = _attribute_name(union.discriminant.name)
        annotations = sorted(
            {self._annotation(arm.type) for _, arm in union.arms if arm is not None}
        )
        arms = ", ".join(
            f"{label}: {self._descriptor(arm.type) if arm else 'None'}"
            for label, arm in union.arms
        )
        return "\n".join(
            [
                "@dataclass",
                f"class {class_name}:",
                f'    """XDR union ``{union.name}``."""',
                "",
                f"    {name}: int",
                f"    value: {' | '.join(annotations)} | None",
                "",
                f'    xdr_discriminant: ClassVar[tuple[str, XdrType]] = ("{name}", '
                f"{self._descriptor(union.discriminant.type)})",
                f"    xdr_arms: ClassVar[dict[int, XdrType | None]] = {{{arms}}}",
            ]
        )

    # types and descriptors

    def _annotation(self, use: TypeUse) -> str:
        """Write the Python type of a declaration.

        :param use: the XDR type.
        :returns: the annotation text.
        """
        base = self._base_annotation(use)
        if use.shape == "optional":
            return f"{base} | None"
        if use.base in ("string", "opaque"):
            return base
        if use.shape in ("fixed", "variable"):
            return f"list[{base}]"
        return base

    def _base_annotation(self, use: TypeUse) -> str:
        """Write the Python type of an item of a declaration.

        :param use: the XDR type.
        :returns: the annotation text.
        """
        if use.base == "string":
            return "str"
        if use.base == "opaque":
            return "bytes"
        if use.base in SIMPLE_TYPES:
            return SIMPLE_TYPES[use.base][1]
        if use.base in self.class_names:
            return self.class_names[use.base]

        typedef = self.by_name.get(use.base)
        if not isinstance(typedef, Typedef):
            raise KeyError(f"unknown type {use.base!r}")
        return self._annotation(typedef.declaration.type)

    def _descriptor(self, use: TypeUse) -> str:
        """Write the ``_xdr`` descriptor of a declaration.

        :param use: the XDR type.
        :returns: the descriptor expression.
        """
        if use.base == "string":
            return f"String({_bound(use.bound)})"
        if use.base == "opaque":
            return self._opaque(use)

        item = self._base_descriptor(use)
        if use.shape == "optional":
            return f"OptionalOf({item})"
        if use.shape == "fixed":
            return f"FixedArray({item}, {use.bound})"
        if use.shape == "variable":
            return f"Array({item}, {_bound(use.bound)})"
        return item

    def _opaque(self, use: TypeUse) -> str:
        """Write the descriptor of an ``opaque`` declaration.

        :param use: the XDR type, with base ``opaque``.
        :returns: the descriptor expression.
        """
        if use.shape == "fixed":
            return f"FixedOpaque({use.bound})"
        return f"VarOpaque({_bound(use.bound)})"

    def _base_descriptor(self, use: TypeUse) -> str:
        """Write the descriptor of an item of a declaration.

        :param use: the XDR type.
        :returns: the descriptor expression.
        """
        if use.base in SIMPLE_TYPES:
            return SIMPLE_TYPES[use.base][0]

        definition = self.by_name.get(use.base)
        if isinstance(definition, Enum):
            return f"EnumType({self.class_names[use.base]})"
        if isinstance(definition, Struct):
            return f"StructType({self.class_names[use.base]})"

        if isinstance(definition, Union):
            return f"UnionType({self.class_names[use.base]})"
        if isinstance(definition, Typedef):
            return self._descriptor(definition.declaration.type)
        raise KeyError(f"unknown type {use.base!r}")

    # procedures

    def _procedure(self, name: str, number: int, driver: str) -> str:
        """Write the ``Procedure`` constant of one call.

        :param name: the lower-case procedure name.
        :param number: the procedure number.
        :param driver: the daemon that serves it.
        :returns: the constant's source.
        """
        args = self._optional_class(f"remote_{name}_args")
        ret = self._optional_class(f"remote_{name}_ret")
        message = self._optional_class(f"remote_{name}_msg")

        extra = f", message={message}" if message else ""
        return (
            f"{name.upper()}: Final = Procedure[{_class_or_none(args)}, "
            f"{_class_or_none(ret)}](\n"
            f'    number={number}, name="{name}", args={_class_value(args)}, '
            f'ret={_class_value(ret)}, driver="{driver}"{extra}\n)'
        )

    def _optional_class(self, struct_name: str) -> str | None:
        """Find the class of an args or ret struct.

        :param struct_name: the XDR struct name, e.g. ``remote_x_args``.
        :returns: the class name, or ``None`` if the call is void there.
        """
        if struct_name not in self.class_names:
            return None
        return self.class_names[struct_name]

    def _check_unique_class_names(self) -> None:
        """Make sure two XDR types do not get the same class name."""
        seen: dict[str, str] = {}
        for xdr_name, class_name in self.class_names.items():
            if class_name in seen:
                raise SystemExit(
                    f"{xdr_name} and {seen[class_name]} are both {class_name}"
                )
            seen[class_name] = xdr_name


def main() -> int:
    """Write (or with ``--check`` verify) the generated protocol modules.

    :returns: the exit status: 1 if ``--check`` finds drift.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only report drift")
    arguments = parser.parse_args()

    drifted = False
    for path, text in generate().items():
        if arguments.check:
            drifted = (
                drifted or not path.exists() or path.read_text(encoding="utf-8") != text
            )
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")

    if drifted:
        print("generated protocol is out of date; run tools/gen_protocol.py")
    return 1 if drifted else 0


def generate() -> dict[Path, str]:
    """Return the text of the generated files.

    :returns: the file paths and their formatted content.
    """
    definitions = load_definitions()
    generator = Generator(definitions)
    drivers = procedure_drivers(generator)
    return {
        OUTPUT / "types.py": _format(_types_file(generator)),
        OUTPUT / "procedures.py": _format(_procedures_file(generator, drivers)),
    }


def load_definitions() -> Definitions:
    """Parse the ``.x`` files of the corpus.

    :returns: the definitions of all of them.
    :raises SystemExit: if the corpus has not been fetched.
    """
    if not SOURCES[0].exists():
        raise SystemExit("run tools/fetch_samples.py first")

    external = {**TYPED_PARAMETER_TYPES, **_header_constants()}
    definitions = Definitions()
    for source in SOURCES:
        definitions.merge(parse(source.read_text(encoding="utf-8"), external))
    return definitions


def procedure_drivers(generator: Generator) -> dict[str, str]:
    """Choose the daemon of every procedure, as libvirt's ``gendispatch.pl`` does.

    :param generator: the indexed definitions.
    :returns: the driver of each procedure name.
    """
    drivers = {}
    for name in generator.procedure_names():
        types = [
            *generator.member_types(f"remote_{name}_args"),
            *generator.member_types(f"remote_{name}_ret"),
        ]
        drivers[name] = connection_driver(_proc_name(name), types)
    return drivers


def connection_driver(proc_name: str, member_types: list[str]) -> str:
    """Port of ``get_conn_method`` of ``src/rpc/gendispatch.pl``.

    :param proc_name: the CamelCase procedure name, e.g. ``ConnectListAllNetworks``.
    :param member_types: the type names of the members of the args and ret structs.
    :returns: the driver that serves the procedure.
    """
    by_type = (
        ("remote_nonnull_interface", "interface"),
        ("remote_nonnull_network", "network"),
        ("remote_nonnull_node_device", "node_device"),
        ("remote_nonnull_nwfilter", "nwfilter"),
        ("remote_nonnull_secret", "secret"),
        ("remote_nonnull_storage", "storage"),
    )
    for member_type in member_types:
        for prefix, driver in by_type:
            if prefix in member_type:
                return driver

    by_name = (
        (r"Connect.*Interface|InterfaceChange", "interface"),
        (r"Connect.*Network", "network"),
        (r"Connect.*NWFilter", "nwfilter"),
        (r"Connect.*Secret", "secret"),
        (r"Connect.*Storage", "storage"),
    )
    if _is_node_device_procedure(proc_name):
        return "node_device"
    for pattern, driver in by_name:
        if re.search(pattern, proc_name):
            return driver
    return "hypervisor"


def _is_node_device_procedure(proc_name: str) -> bool:
    """Tell whether a procedure belongs to the node device daemon.

    A few ``NodeDevice*`` procedures are handled by the virt drivers.

    :param proc_name: the CamelCase procedure name.
    :returns: ``True`` for the node device daemon.
    """
    if not re.search(r"Node.*Device", proc_name):
        return False
    hypervisor_ones = (
        "NodeDeviceReset",
        "NodeDeviceReAttach",
        "NodeDeviceDettach",
        "NodeDeviceDetachFlags",
    )
    return not any(name in proc_name for name in hypervisor_ones)


def _proc_name(name: str) -> str:
    """Port of ``name_to_ProcName`` of ``gendispatch.pl``.

    :param name: a procedure name such as ``connect_list_all_networks``.
    :returns: the CamelCase name, e.g. ``ConnectListAllNetworks``.
    """
    fixups = (
        (r"Nwfilter", "NWFilter"),
        (r"Xml$", "XML"),
        (r"Xml2$", "XML2"),
        (r"Uri$", "URI"),
        (r"Uuid$", "UUID"),
        (r"Id$", "ID"),
        (r"Mac$", "MAC"),
        (r"Cpu$", "CPU"),
        (r"Os$", "OS"),
        (r"Nmi$", "NMI"),
        (r"Pm", "PM"),
        (r"Fstrim$", "FSTrim"),
        (r"Fsfreeze$", "FSFreeze"),
        (r"Fsthaw$", "FSThaw"),
        (r"Fsinfo$", "FSInfo"),
        (r"Iothread$", "IOThread"),
        (r"Scsi", "SCSI"),
        (r"Wwn$", "WWN"),
        (r"Dhcp$", "DHCP"),
    )
    words = []
    for part in name.split("_"):
        word = part.capitalize()
        for pattern, replacement in fixups:
            word = re.sub(pattern, replacement, word, count=1)
        words.append(word)
    return "".join(words)


def _header_constants() -> dict[str, int]:
    """Read the buffer sizes the protocol takes from ``libvirt-host.h``.

    :returns: name -> value.
    :raises SystemExit: if a constant is missing or not a simple sum.
    """
    header = (CORPUS / "include" / "libvirt" / "libvirt-host.h").read_text(
        encoding="utf-8"
    )
    found = {}
    for name in HEADER_CONSTANTS:
        match = re.search(rf"#\s*define\s+{name}\s+\(([0-9 +]+)\)", header)
        if match is None:
            raise SystemExit(f"{name} not found in libvirt-host.h")
        found[name] = sum(int(part) for part in match.group(1).split("+"))
    return found


def _types_file(generator: Generator) -> str:
    """Wrap the generated types in a module with its header.

    :param generator: the indexed definitions.
    :returns: the unformatted module source.
    """
    body = generator.types_module()
    descriptors = [
        "BOOL", "DOUBLE", "FLOAT", "HYPER", "INT", "UHYPER", "UINT", "Array",
        "EnumType", "FixedArray", "FixedOpaque", "OptionalOf", "String",
        "StructType", "UnionType", "VarOpaque",
    ]  # fmt: skip
    used = [name for name in descriptors if re.search(rf"\b{name}\b", body)]
    header = (
        '"""GENERATED by tools/gen_protocol.py. Do not edit.\n\n'
        "Derived from libvirt's remote_protocol.x (LGPL-2.1-or-later).\n\n"
        "The wire structures of the libvirt remote protocol. Each dataclass carries\n"
        "the XDR layout (``xdr_fields``) that ``libvirtpy.rpc.xdr`` encodes.\n"
        '"""\n\n'
        "from dataclasses import dataclass\n"
        "from enum import IntEnum\n"
        "from typing import ClassVar, Final\n\n"
        "from libvirtpy.rpc.xdr import XdrType, " + ", ".join(used) + "\n"
    )
    return header + "\n\n" + body + "\n"


def _procedures_file(generator: Generator, drivers: dict[str, str]) -> str:
    """Wrap the generated procedures in a module with its header.

    :param generator: the indexed definitions.
    :param drivers: the daemon of each procedure.
    :returns: the unformatted module source.
    """
    body = generator.procedures_module(drivers)
    imports = sorted(
        name
        for name in generator.class_names.values()
        if re.search(rf"\b{name}\b", body)
    )
    header = '''"""GENERATED by tools/gen_protocol.py. Do not edit.

Derived from libvirt's remote_protocol.x (LGPL-2.1-or-later).

Every procedure of the libvirt remote protocol, by number and by name.
"""

from typing import Any, Final

from libvirtpy.rpc.procedure import Procedure
from libvirtpy.rpc.protocol.types import (
'''
    header += "".join(f"    {name},\n" for name in imports) + ")\n"
    return header + "\n\n" + body + "\n"


def _format(text: str) -> str:
    """Sort the imports of ``text`` and format it like the rest of the project.

    :param text: Python source.
    :returns: the sorted, formatted source.
    """
    filename = str(OUTPUT / "generated.py")
    sort_imports = [
        "check",
        "--fix-only",
        "--select",
        "I",
        "--stdin-filename",
        filename,
        "-",
    ]
    return _run_ruff(
        ["format", "--stdin-filename", filename, "-"], _run_ruff(sort_imports, text)
    )


def _run_ruff(arguments: list[str], text: str) -> str:
    """Run ruff on ``text`` through its standard input.

    :param arguments: the ruff command line after ``ruff``.
    :param text: the source to process.
    :returns: ruff's output.
    """
    result = subprocess.run(
        [sys.executable, "-m", "ruff", *arguments],
        input=text,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _class_name(xdr_name: str) -> str:
    """Make a Python class name from an XDR type name.

    :param xdr_name: e.g. ``remote_domain_lookup_by_name_args``.
    :returns: e.g. ``DomainLookupByNameArgs``.
    """
    if "_" not in xdr_name:
        return xdr_name[0].upper() + xdr_name[1:]
    words = xdr_name.removeprefix("remote_").split("_")
    return "".join(word.capitalize() for word in words)


def _attribute_name(xdr_name: str) -> str:
    """Make a Python attribute name from an XDR member name.

    :param xdr_name: the member name, possibly camelCase (``callbackID``).
    :returns: the snake_case name (``callback_id``), with ``_`` added if it is a
        Python keyword.
    """
    snake = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", xdr_name).lower()
    return f"{snake}_" if keyword.iskeyword(snake) else snake


def _common_prefix(names: list[str]) -> str:
    """Find the words that start every name of an enum.

    :param names: the member names, e.g. ``VIR_NET_CALL``, ``VIR_NET_REPLY``.
    :returns: the shared prefix with its trailing underscore, e.g. ``VIR_NET_``.
    """
    split = [name.split("_") for name in names]
    shared: list[str] = []
    for words in zip(*split, strict=False):
        if len(set(words)) != 1:
            break
        shared.append(words[0])
    shared = shared[: min(len(parts) for parts in split) - 1]
    return "".join(f"{word}_" for word in shared)


def _member_name(name: str, prefix: str) -> str:
    """Strip an enum's common prefix from a member name.

    :param name: the XDR member name.
    :param prefix: the common prefix of the enum.
    :returns: the Python member name.
    """
    stripped = name.removeprefix(prefix)
    return stripped if stripped.isidentifier() else name


def _bound(bound: int | None) -> str:
    """Write the bound of a variable-length item.

    :param bound: the ``N`` of ``<N>``, or ``None`` for ``<>``.
    :returns: the argument text.
    """
    return "" if bound is None else str(bound)


def _class_or_none(class_name: str | None) -> str:
    """Write a type argument for ``Procedure[...]``.

    :param class_name: the class, or ``None`` for void.
    :returns: the class name or ``None``.
    """
    return class_name or "None"


def _class_value(class_name: str | None) -> str:
    """Write the class argument of a ``Procedure``.

    :param class_name: the class, or ``None`` for void.
    :returns: the class name or ``None``.
    """
    return class_name or "None"


if __name__ == "__main__":
    sys.exit(main())
