"""Generate the two clients from the operation modules.

Every public function of the modules of ``libvirtpy/client/operations/``
becomes a one-line method of ``LibvirtClient`` (``client.py``) and of
``AsyncLibvirtClient`` (``aio.py``), with its signature and docstring. A
function whose first parameter is a reference (``DomainRef``, ``PoolRef``, ...)
also becomes a method of that kind's proxy, with the reference filled in
(``client.domain("vm").set_vcpus(4)``).

Usage: ``python tools/gen_client.py [--check]``; ``--check`` only reports drift.
"""

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

CLIENT_DIRECTORY = (
    Path(__file__).resolve().parent.parent / "src" / "libvirtpy" / "client"
)
OPERATIONS_DIRECTORY = CLIENT_DIRECTORY / "operations"

# The type of a first parameter -> (proxy class name, kind in the method names).
PROXY_KINDS = {
    "DomainRef": ("Domain", "domain"),
    "NetworkRef": ("Network", "network"),
    "PoolRef": ("Pool", "pool"),
    "SecretRef": ("Secret", "secret"),
    "NwFilterRef": ("NwFilter", "nwfilter"),
    "HostInterfaceRef": ("HostInterface", "host_interface"),
    "NodeDeviceRef": ("NodeDevice", "node_device"),
}


@dataclass(frozen=True)
class Operation:
    """A public function of the operation modules."""

    name: str
    node: ast.FunctionDef
    result: str
    """The ``T`` of ``Operation[T]``, as source text."""

    @property
    def documentation(self) -> str:
        """The operation's docstring."""
        return ast.get_docstring(self.node) or ""

    @property
    def first_parameter_type(self) -> str | None:
        """The annotation of the first parameter, as source text."""
        arguments = self.node.args.args
        if not arguments or arguments[0].annotation is None:
            return None
        return ast.unparse(arguments[0].annotation)


@dataclass(frozen=True)
class Flavor:
    """What differs between the sync and the async client."""

    prefix: str
    base: str
    keyword: str
    wait: str

    def translate(self, text: str) -> str:
        """Rewrite a type of an operation for this client.

        The stream operations return ``RemoteStream``; the async client returns
        ``AsyncRemoteStream``.

        :param text: a type annotation as source text.
        :returns: the annotation for this client.
        """
        if not self.prefix:
            return text
        return re.sub(r"\bRemoteStream\b", "AsyncRemoteStream", text)

    @classmethod
    def for_async(cls, *, is_async: bool) -> Flavor:
        """Pick the flavor.

        :param is_async: ``True`` for the async client.
        :returns: the flavor.
        """
        if is_async:
            return cls("Async", "AsyncClientBase", "async def", "await ")
        return cls("", "SyncClientBase", "def", "")


def main() -> int:
    """Write (or with ``--check`` verify) the generated clients.

    :returns: the exit status: 1 if ``--check`` finds drift.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only report drift")
    arguments = parser.parse_args()

    drifted = False
    for path, text in generate().items():
        if arguments.check:
            drifted = drifted or path.read_text(encoding="utf-8") != text
            continue
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")

    if drifted:
        print("generated clients are out of date; run tools/gen_client.py")
    return 1 if drifted else 0


def generate() -> dict[Path, str]:
    """Return the text of the generated files.

    :returns: the file paths and their formatted content.
    """
    operations: list[Operation] = []
    imports: dict[str, str] = {}
    for path in sorted(OPERATIONS_DIRECTORY.glob("[!_]*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        operations += _operations(tree)
        imports.update(_imports(tree))
    return {
        CLIENT_DIRECTORY / "client.py": _render(operations, imports, is_async=False),
        CLIENT_DIRECTORY / "aio.py": _render(operations, imports, is_async=True),
    }


def _operations(tree: ast.Module) -> list[Operation]:
    """Collect the public operations of the module.

    :param tree: the parsed the operation modules.
    :returns: one entry per public function, in file order.
    :raises SystemExit: if a public function does not return ``Operation[...]``.
    """
    found = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
            continue

        returns = node.returns
        is_operation = (
            isinstance(returns, ast.Subscript)
            and isinstance(returns.value, ast.Name)
            and returns.value.id == "Operation"
        )
        if not is_operation or not isinstance(returns, ast.Subscript):
            raise SystemExit(f"{node.name} must return Operation[...]")

        found.append(Operation(node.name, node, ast.unparse(returns.slice)))
    return found


def _imports(tree: ast.Module) -> dict[str, str]:
    """Map each name imported by the operation modules to its module.

    :param tree: the parsed the operation modules.
    :returns: name -> module.
    """
    names = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                names[alias.asname or alias.name] = node.module
    return names


def _render(
    operations: list[Operation], imports: dict[str, str], *, is_async: bool
) -> str:
    """Build one generated file.

    :param operations: the operations to turn into methods.
    :param imports: the imports of the operation modules, name -> module.
    :param is_async: whether to build the async client.
    :returns: the formatted file content.
    """
    flavor = Flavor.for_async(is_async=is_async)
    kinds = _proxy_kinds(operations)
    classes = [_client_class(operations, kinds, flavor)]
    classes += [_proxy_class(kind, operations, flavor) for kind in kinds.values()]

    text = "\n\n\n".join(classes)
    header = _header(text, imports, flavor)
    return _format(header + "\n\n\n" + text + "\n")


def _proxy_kinds(operations: list[Operation]) -> dict[str, tuple[str, str]]:
    """Select the proxy kinds that at least one operation uses.

    :param operations: all the operations.
    :returns: reference type -> (proxy name, kind), for the kinds in use.
    """
    used = {operation.first_parameter_type for operation in operations}
    return {ref: kind for ref, kind in PROXY_KINDS.items() if ref in used}


def _client_class(
    operations: list[Operation],
    kinds: dict[str, tuple[str, str]],
    flavor: Flavor,
) -> str:
    """Build the source of the client class.

    :param operations: the operations to turn into methods.
    :param kinds: the proxies the client can create.
    :param flavor: sync or async.
    :returns: the class source.
    """
    awaitable = ", with awaitable methods" if flavor.prefix else ""
    lines = [
        f"class {flavor.prefix}LibvirtClient({flavor.base}):",
        f'    """A client of a libvirt daemon{awaitable}.',
        "",
        "    Every method is generated from the operation of the same name in",
        "    ``libvirtpy.client.operations``.",
        '    """',
        "",
    ]

    for operation in operations:
        lines += _method(operation, flavor, proxy_method=None)

    for reference, (proxy, kind) in kinds.items():
        spoken = kind.replace("_", " ")
        proxy_class = f"{flavor.prefix}{proxy}Proxy"
        lines += [
            f"    def {kind}(self, {kind}: {reference}) -> {proxy_class}:",
            f'        """Return a proxy that fills in ``{kind}`` for its operations.',
            "",
            f"        :param {kind}: the {spoken} to act on.",
            f"        :returns: the proxy, e.g. ``client.{kind}(x).start()``.",
            '        """',
            f"        return {proxy_class}(self, {kind})",
            "",
        ]
    return "\n".join(lines).rstrip()


def _proxy_class(
    kind: tuple[str, str], operations: list[Operation], flavor: Flavor
) -> str:
    """Build the source of one proxy class.

    :param kind: (proxy name, kind) of the proxy.
    :param operations: all the operations; the ones of this kind become methods.
    :param flavor: sync or async.
    :returns: the class source.
    :raises SystemExit: if two operations get the same proxy method name.
    """
    proxy, word = kind
    reference = next(ref for ref, known in PROXY_KINDS.items() if known == kind)
    spoken = word.replace("_", " ")
    lines = [
        f"class {flavor.prefix}{proxy}Proxy:",
        f'    """The operations on one {spoken}, with it filled in."""',
        "",
        "    def __init__(",
        f"        self, client: {flavor.prefix}LibvirtClient, {word}: {reference}",
        "    ) -> None:",
        '        """Create the proxy.',
        "",
        "        :param client: the client the operations go through.",
        f"        :param {word}: the {spoken} they act on.",
        '        """',
        "        self._client = client",
        f"        self._reference = {word}",
        "",
    ]

    seen = set()
    for operation in operations:
        if operation.first_parameter_type != reference:
            continue

        method = _proxy_method_name(operation.name, word)
        if method in seen:
            raise SystemExit(f"duplicate proxy method {proxy}Proxy.{method}")
        seen.add(method)

        lines += _method(operation, flavor, proxy_method=method)
    return "\n".join(lines).rstrip()


def _method(
    operation: Operation, flavor: Flavor, *, proxy_method: str | None
) -> list[str]:
    """Build the source lines of one method.

    :param operation: the operation the method wraps.
    :param flavor: sync or async.
    :param proxy_method: for a proxy, the method name; ``None`` for the client.
    :returns: the method's lines, ending with a blank line.
    """
    is_proxy = proxy_method is not None
    parameters, call = _parameters(operation, drop_first=is_proxy)
    arguments = ", ".join(call)

    if is_proxy:
        statement = f"return {flavor.wait}self._client.{operation.name}({arguments})"
    else:
        operation_call = f"operations.{operation.name}({arguments})"
        translated = flavor.translate(operation.result)
        if translated != operation.result:
            # The operation is written for the blocking client; only its result
            # type differs, so tell the type checker what the async client gets.
            operation_call = f'cast("Operation[{translated}]", {operation_call})'
        statement = f"return {flavor.wait}self._run({operation_call})"

    name = proxy_method or operation.name
    signature = (
        f"{flavor.keyword} {name}({', '.join(parameters)}) -> "
        f"{flavor.translate(operation.result)}:"
    )
    documentation = _documentation(operation, drop_first=is_proxy)
    return [
        f"    {signature}",
        *[f"        {line}" if line else "" for line in documentation],
        f"        {statement}",
        "",
    ]


def _parameters(
    operation: Operation, *, drop_first: bool
) -> tuple[list[str], list[str]]:
    """Build a method's parameter list and the arguments it passes on.

    :param operation: the operation the method wraps.
    :param drop_first: leave out the first parameter (a proxy fills it in).
    :returns: the parameter declarations and the call arguments.
    """
    arguments = operation.node.args
    required = len(arguments.args) - len(arguments.defaults)
    defaults = [None] * required + list(arguments.defaults)

    positional = list(zip(arguments.args, defaults, strict=True))
    if drop_first:
        positional = positional[1:]

    parameters = ["self"]
    call = ["self._reference"] if drop_first else []
    for argument, default in positional:
        parameters.append(_parameter(argument, default))
        call.append(argument.arg)

    if arguments.kwonlyargs:
        parameters.append("*")
    keyword_only = zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True)
    for argument, default in keyword_only:
        parameters.append(_parameter(argument, default))
        call.append(f"{argument.arg}={argument.arg}")
    return parameters, call


def _parameter(argument: ast.arg, default: ast.expr | None) -> str:
    """Write one parameter declaration.

    :param argument: the parameter.
    :param default: its default value, if any.
    :returns: e.g. ``flags: int = 0``.
    """
    annotation = f": {ast.unparse(argument.annotation)}" if argument.annotation else ""
    suffix = f" = {ast.unparse(default)}" if default is not None else ""
    return f"{argument.arg}{annotation}{suffix}"


def _documentation(operation: Operation, *, drop_first: bool) -> list[str]:
    """Build the quoted docstring lines of a method.

    :param operation: the operation the method wraps.
    :param drop_first: leave out the ``:param:`` of the first parameter.
    :returns: the docstring, with its quotes.
    """
    lines = operation.documentation.splitlines()
    if drop_first:
        lines = _without_parameter(lines, operation.node.args.args[0].arg)

    if len(lines) == 1:
        return [f'"""{lines[0]}"""']
    return [f'"""{lines[0]}', *lines[1:], '"""']


def _without_parameter(lines: list[str], name: str) -> list[str]:
    """Remove the ``:param name:`` field (and its continuation lines).

    :param lines: the docstring lines.
    :param name: the parameter to remove.
    :returns: the remaining lines.
    """
    kept = []
    skipping = False
    for line in lines:
        if line.startswith(f":param {name}:"):
            skipping = True
            continue
        if skipping and line.startswith("    "):
            continue

        skipping = False
        kept.append(line)
    return kept


def _proxy_method_name(operation: str, kind: str) -> str:
    """Shorten an operation name for a proxy: drop the kind word.

    :param operation: e.g. ``set_domain_vcpus``.
    :param kind: e.g. ``domain``.
    :returns: e.g. ``set_vcpus``.
    """
    stripped = re.sub(rf"(^|_){kind}(?=_|$)", "", operation).lstrip("_")
    return stripped or operation


def _header(text: str, imports: dict[str, str], flavor: Flavor) -> str:
    """Build the docstring and imports of a generated file.

    :param text: the generated classes, to find which imports are used.
    :param imports: the imports of the operation modules, name -> module.
    :param flavor: sync or async.
    :returns: the header text.
    """
    used = {node.id for node in ast.walk(ast.parse(text)) if isinstance(node, ast.Name)}
    by_module: dict[str, list[str]] = {}
    for name, module in imports.items():
        if name in used:
            by_module.setdefault(module, []).append(name)

    lines = [
        '"""GENERATED by tools/gen_client.py from the operation modules. Do not edit.',
        "",
        "Regenerate with ``python tools/gen_client.py`` after changing an operation.",
        '"""',
        "",
        "from libvirtpy.client import operations",
        f"from libvirtpy.client._bases import {flavor.base}",
    ]
    for module, names in sorted(by_module.items()):
        lines.append(f"from {module} import {', '.join(sorted(names))}")
    if "cast(" in text:
        lines += [
            "from typing import cast",
            "from libvirtpy.client.transport import Operation",
        ]
    return "\n".join(lines)


def _format(text: str) -> str:
    """Format the generated source and add ``__all__`` after the imports.

    :param text: the generated source.
    :returns: the formatted file content.
    """
    formatted = _ruff(text)
    classes = [
        node.name
        for node in ast.parse(formatted).body
        if isinstance(node, ast.ClassDef)
    ]
    exports = "__all__ = [" + ", ".join(f'"{name}"' for name in sorted(classes)) + "]"

    position = formatted.index("\n\n\nclass ")
    return _ruff(formatted[:position] + "\n\n" + exports + formatted[position:])


def _ruff(text: str) -> str:
    """Sort the imports and format ``text`` like the rest of the project.

    :param text: Python source.
    :returns: the sorted, formatted source.
    """
    filename = str(CLIENT_DIRECTORY / "generated.py")
    sort_imports = [
        "check",
        "--fix-only",
        "--select",
        "I",
        "--stdin-filename",
        filename,
        "-",
    ]
    sorted_text = _run_ruff(sort_imports, text)
    return _run_ruff(["format", "--stdin-filename", filename, "-"], sorted_text)


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


if __name__ == "__main__":
    sys.exit(main())
