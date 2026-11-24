"""Compare libvirt's RelaxNG schemas with our models.

Both sides are reduced to a set of paths such as ``/domain/devices/disk/@type``
(elements and attributes, no values). Paths only in the schema are not
modelled yet; paths only in the models are mistakes (a wrong tag or
attribute name), since every element we model must exist in the schema.

Recursive structures (``<backingStore>`` inside ``<backingStore>``) are
expanded once.

Usage: ``python tools/schema_coverage.py [--under /domain/devices] [--depth 3]``
Needs the corpus: ``python tools/fetch_samples.py``.
"""

import argparse
import sys
import types
import typing
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree
from pydantic_xml.fields import XmlEntityInfoP, extract_field_xml_entity_info
from pydantic_xml.typedefs import EntityLocation

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml.backup import Backup, Checkpoint
from libvirtpy.xml.capabilities import (
    Capabilities,
    DomainCapabilities,
    StoragePoolCapabilities,
)
from libvirtpy.xml.domain import Domain
from libvirtpy.xml.interface import HostInterface
from libvirtpy.xml.network import Network, NetworkPort
from libvirtpy.xml.nodedev import Device
from libvirtpy.xml.nwfilter import Filter, FilterBinding
from libvirtpy.xml.secret import Secret
from libvirtpy.xml.snapshot import Snapshot
from libvirtpy.xml.storage import Pool, Volume
from libvirtpy.xml.sysinfo import Sysinfo

RELAXNG_NS = "http://relaxng.org/ns/structure/1.0"
SCHEMA_DIR = Path(__file__).resolve().parent.parent / ".cache/libvirt/src/conf/schemas"

# Root models and the schema that describes them.
ROOT_MODELS: dict[str, tuple[str, type[LibvirtXmlModel]]] = {
    "domain": ("domain.rng", Domain),
    "network": ("network.rng", Network),
    "pool": ("storagepool.rng", Pool),
    "secret": ("secret.rng", Secret),
    "nodedev": ("nodedev.rng", Device),
    "backup": ("domainbackup.rng", Backup),
    "snapshot": ("domainsnapshot.rng", Snapshot),
    "checkpoint": ("domaincheckpoint.rng", Checkpoint),
    "domaincaps": ("domaincaps.rng", DomainCapabilities),
    "capabilities": ("capability.rng", Capabilities),
    "filter": ("nwfilter.rng", Filter),
    "interface": ("interface.rng", HostInterface),
    "networkport": ("networkport.rng", NetworkPort),
    "filterbinding": ("nwfilterbinding.rng", FilterBinding),
    "storagepoolcaps": ("storagepoolcaps.rng", StoragePoolCapabilities),
    "sysinfo": ("sysinfo.rng", Sysinfo),
    "volume": ("storagevol.rng", Volume),
}


# Paths a model has on purpose although the schema does not allow them:
# - the snapshot reuses the domain's disk source models, which also allow a few
#   attributes that ``domainsnapshot.rng`` forbids (libvirt rejects them there);
# - the daemon writes things its own schema does not list (found by round-tripping
#   a real daemon's XML, see ``tests/live/test_live_roundtrip.py``): the ``index``
#   of the disks of a running backup job.
# Entries are path suffixes, matched with ``str.endswith``/``in``.
KNOWN_SHARED_MODEL_EXTRAS: dict[str, tuple[str, ...]] = {
    "backup": ("/disks/disk/@index",),
    "snapshot": (
        "/source/@fdgroup",
        "/source/@startupPolicy",
        "/source/reservations",
    ),
}


@dataclass
class Grammar:
    """The ``<define>``s and ``<start>`` of one (possibly nested) grammar."""

    defines: dict[str, list[etree._Element]] = field(default_factory=dict)
    starts: list[etree._Element] = field(default_factory=list)
    parent: Grammar | None = None


def load_grammar_file(path: Path, parent: Grammar | None = None) -> Grammar:
    """Load a ``.rng`` file, following ``<include>`` like a RelaxNG processor.

    :param path: the schema file.
    :param parent: the grammar this one is nested in, for ``<parentRef>``.
    :returns: the definitions and start patterns of the file and its includes.
    """
    root = etree.parse(str(path)).getroot()
    grammar = Grammar(parent=parent)
    _collect_grammar(root, path.parent, grammar)
    return grammar


@dataclass
class SchemaWalker:
    """Expands a grammar into the set of element and attribute paths."""

    base_dir: Path
    paths: set[str] = field(default_factory=set)

    def walk_grammar(self, grammar: Grammar, path: str) -> None:
        """Walk the start patterns of ``grammar``.

        :param grammar: the grammar to expand.
        :param path: the path of the element that contains the grammar.
        """
        for pattern in grammar.starts:
            self.walk(pattern, grammar, path, frozenset())

    def walk(
        self,
        pattern: etree._Element,
        grammar: Grammar,
        path: str,
        active_defines: frozenset[str],
    ) -> None:
        """Walk one pattern and record the element and attribute paths below it.

        :param pattern: the RelaxNG pattern to walk.
        :param grammar: the grammar that resolves ``<ref>`` names.
        :param path: the path of the element that contains the pattern.
        :param active_defines: the defines being expanded, to stop a recursion.
        """
        tag = pattern.tag
        if tag == _rng("element"):
            self._walk_element(pattern, grammar, path, active_defines)
        elif tag == _rng("attribute"):
            self._record_attribute(pattern, path)
        elif tag in (_rng("ref"), _rng("parentRef")):
            self._walk_ref(pattern, grammar, path, active_defines)
        elif tag == _rng("grammar"):
            nested = Grammar(parent=grammar)
            _collect_grammar(pattern, self.base_dir, nested)
            self.walk_grammar(nested, path)
        else:  # group, choice, optional, interleave, data, value, ...
            for child in pattern:
                self.walk(child, grammar, path, active_defines)

    def _walk_element(
        self,
        pattern: etree._Element,
        grammar: Grammar,
        path: str,
        active_defines: frozenset[str],
    ) -> None:
        """Record an ``<element>`` pattern and walk its content.

        :param pattern: the ``<element>`` pattern.
        :param grammar: the grammar that resolves ``<ref>`` names.
        :param path: the path of the element that contains the pattern.
        :param active_defines: the defines being expanded, to stop a recursion.
        """
        name = _pattern_name(pattern, element=True)
        if name is None:  # <anyName/>: arbitrary content such as <metadata>
            self.paths.add(f"{path}/*")
            return

        if f"/{name}/" in f"{path}/":
            # A recursive structure (<backingStore> in <backingStore>) is
            # expanded once; the model side applies the same rule.
            return

        element_path = f"{path}/{name}"
        self.paths.add(element_path)
        # Recursion through an element is cut by the rule above, so the
        # chain of active defines starts again inside every element.
        for child in pattern:
            self.walk(child, grammar, element_path, frozenset())

    def _record_attribute(self, pattern: etree._Element, path: str) -> None:
        """Record an ``<attribute>`` pattern.

        :param pattern: the ``<attribute>`` pattern.
        :param path: the path of the element that has the attribute.
        """
        name = _pattern_name(pattern, element=False)
        self.paths.add(f"{path}/@{name if name is not None else '*'}")

    def _walk_ref(
        self,
        pattern: etree._Element,
        grammar: Grammar,
        path: str,
        active_defines: frozenset[str],
    ) -> None:
        """Expand a ``<ref>`` or ``<parentRef>`` unless it is already being expanded.

        :param pattern: the reference pattern.
        :param grammar: the grammar the reference is in.
        :param path: the path of the element that contains the pattern.
        :param active_defines: the defines being expanded, to stop a recursion.
        """
        scope = grammar
        if pattern.tag == _rng("parentRef") and grammar.parent is not None:
            scope = grammar.parent

        name = str(pattern.get("name"))
        key = f"{id(scope)}:{name}"
        if key in active_defines:  # recursive structure: expand only once
            return

        for define in scope.defines.get(name, []):
            for child in define:
                self.walk(child, scope, path, active_defines | {key})


def schema_paths(schema_file: Path) -> set[str]:
    """Return every element and attribute path that ``schema_file`` allows.

    :param schema_file: a ``.rng`` file.
    :returns: paths like ``/domain/devices/disk/@type``.
    """
    grammar = load_grammar_file(schema_file)
    walker = SchemaWalker(base_dir=schema_file.parent)
    walker.walk_grammar(grammar, "")
    return walker.paths


def model_paths(model: type[LibvirtXmlModel]) -> set[str]:
    """Return every element and attribute path that ``model`` reads and writes.

    :param model: the root model of a document.
    :returns: paths in the same form as ``schema_paths``.
    """
    paths: set[str] = set()
    root_path = f"/{model.__xml_tag__}"
    paths.add(root_path)

    _collect_model_paths(model, root_path, paths, frozenset())
    return paths


@dataclass(frozen=True)
class Coverage:
    schema: set[str]
    modelled: set[str]
    allowed_extras: tuple[str, ...] = ()

    @property
    def covered(self) -> set[str]:
        return self.schema & self.modelled

    @property
    def missing(self) -> set[str]:
        return self.schema - self.modelled

    @property
    def unknown(self) -> set[str]:
        """Modelled paths the schema does not allow: a mistake, unless listed."""
        return {
            path
            for path in self.modelled - self.schema
            if not any(extra in path for extra in self.allowed_extras)
        }


def coverage(root: str) -> Coverage:
    """Compare the schema and the model of one document type.

    :param root: a key of ``ROOT_MODELS``, e.g. ``"domain"``.
    :returns: the schema paths, the model paths and the allowed extras.
    """
    schema_file, model = ROOT_MODELS[root]
    return Coverage(
        schema=schema_paths(SCHEMA_DIR / schema_file),
        modelled=model_paths(model),
        allowed_extras=KNOWN_SHARED_MODEL_EXTRAS.get(root, ()),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default="domain", choices=ROOT_MODELS)
    parser.add_argument("--under", default=None, help="only paths below this one")
    parser.add_argument("--depth", type=int, default=None, help="levels below --under")
    arguments = parser.parse_args()

    if not SCHEMA_DIR.is_dir():
        print("error: no corpus; run python tools/fetch_samples.py", file=sys.stderr)
        return 1

    result = coverage(arguments.root)
    root_model = ROOT_MODELS[arguments.root][1]
    under = arguments.under or f"/{root_model.__xml_tag__}"

    schema = _limit(result.schema, under=under, depth=None)
    covered = _limit(result.covered, under=under, depth=None)
    print(f"{under}: {len(covered)}/{len(schema)} schema paths modelled")

    for path in _limit(result.unknown, under=under, depth=None):
        print(f"  NOT IN SCHEMA  {path}")
    for path in _limit(result.missing, under=under, depth=arguments.depth):
        print(f"  missing        {path}")

    return 0


def _rng(tag: str) -> str:
    """Return ``tag`` as a name in the RelaxNG namespace.

    :param tag: a RelaxNG element name, e.g. ``"element"``.
    :returns: the name in ``{namespace}tag`` form.
    """
    return f"{{{RELAXNG_NS}}}{tag}"


def _collect_grammar(node: etree._Element, base_dir: Path, grammar: Grammar) -> None:
    """Add the definitions found directly in ``node`` (a grammar or ``<div>``).

    :param node: the element to read.
    :param base_dir: the directory that ``<include>`` paths are relative to.
    :param grammar: the grammar to add the definitions to.
    """
    for child in node:
        if child.tag == _rng("start"):
            grammar.starts.extend(child)
        elif child.tag == _rng("define"):
            _add_define(grammar, child)
        elif child.tag == _rng("div"):
            _collect_grammar(child, base_dir, grammar)
        elif child.tag == _rng("include"):
            _include(child, base_dir, grammar)


def _add_define(grammar: Grammar, define: etree._Element) -> None:
    """Add a ``<define>`` to the grammar; ``combine`` adds to an existing name.

    :param grammar: the grammar to add to.
    :param define: the ``<define>`` element.
    """
    name = str(define.get("name"))
    if define.get("combine") is None:
        grammar.defines[name] = [define]
        return
    grammar.defines.setdefault(name, []).append(define)


def _include(include: etree._Element, base_dir: Path, grammar: Grammar) -> None:
    """Add the content of an ``<include>`` to the grammar.

    :param include: the ``<include>`` element; its children override the file's.
    :param base_dir: the directory that ``href`` is relative to.
    :param grammar: the grammar to add to.
    """
    included_path = base_dir / str(include.get("href"))
    included = load_grammar_file(included_path, parent=grammar.parent)

    overrides = Grammar()
    _collect_grammar(include, base_dir, overrides)

    # Definitions inside <include> replace the included file's ones.
    included.defines.update(overrides.defines)
    if overrides.starts:
        included.starts = overrides.starts

    for name, bodies in included.defines.items():
        grammar.defines.setdefault(name, []).extend(bodies)
    grammar.starts.extend(included.starts)


def _pattern_name(pattern: etree._Element, *, element: bool) -> str | None:
    """Return the Clark name of an ``<element>``/``<attribute>`` pattern.

    Elements inherit the ``ns`` attribute of the nearest ancestor; attributes
    only use their own. Returns ``None`` for wildcard names (``<anyName/>``).

    :param pattern: the ``<element>`` or ``<attribute>`` pattern.
    :param element: whether the pattern is an element (it inherits ``ns``).
    :returns: the name, or ``None`` for a wildcard.
    """
    local_name = pattern.get("name")
    if local_name is None:
        name_child = pattern.find(_rng("name"))
        if name_child is None or name_child.text is None:
            return None
        local_name = name_child.text.strip()

    namespace = _inherited_namespace(pattern) if element else pattern.get("ns", "")
    if ":" in local_name or not namespace:
        return local_name
    return f"{{{namespace}}}{local_name}"


def _inherited_namespace(pattern: etree._Element) -> str:
    """Return the ``ns`` attribute of the nearest ancestor that has one.

    :param pattern: the pattern to start from.
    :returns: the namespace URI, or ``""`` if no ancestor sets one.
    """
    node: etree._Element | None = pattern
    while node is not None:
        namespace = node.get("ns")
        if namespace is not None:
            return namespace
        node = node.getparent()
    return ""


def _collect_model_paths(
    model: type[LibvirtXmlModel],
    path: str,
    paths: set[str],
    active_models: frozenset[type[LibvirtXmlModel]],
) -> None:
    """Add the paths of ``model``'s fields, and of the models in them, to ``paths``.

    :param model: the model to read.
    :param path: the path of the element that the model describes.
    :param paths: the set to add the paths to.
    :param active_models: the models being expanded, to stop a recursion.
    """
    if model in active_models:
        return

    for field_name, field_info in model.model_fields.items():
        if field_name in model.__xml_field_validators__:
            # A field with its own XML reader takes arbitrary children, like
            # the schema's <anyName/>: ``Metadata.elements``.
            paths.add(f"{path}/*")
            continue

        entity = extract_field_xml_entity_info(field_info)
        submodels = list(_submodels(field_info.annotation))
        if entity is None and not submodels:
            continue  # element text

        if entity is not None and entity.location == EntityLocation.ATTRIBUTE:
            paths.add(f"{path}/@{entity.path or field_name}")
            continue

        tags = [entity.path] if entity is not None and entity.path else []
        if not tags:
            tags = [str(submodel.__xml_tag__) for submodel in submodels]

        for plain_tag in tags:
            tag = _qualified_tag(plain_tag, entity, submodels, model)
            if f"/{tag}/" in f"{path}/":
                # A recursive structure (<backingStore> in <backingStore>, or
                # <source><dataStore><source>) is not expanded again, like the
                # schema side does.
                continue

            element_path = f"{path}/{tag}"
            paths.add(element_path)
            for submodel in submodels:
                _collect_model_paths(
                    submodel, element_path, paths, active_models | {model}
                )


def _qualified_tag(
    tag: str,
    entity: XmlEntityInfoP | None,
    submodels: list[type[LibvirtXmlModel]],
    parent: type[LibvirtXmlModel],
) -> str:
    """Return ``tag`` as ``{namespace-uri}tag`` if the field is namespaced.

    The prefix comes from the field (``element(ns="qemu")``) or from the model
    it holds; it is resolved with the namespace maps of those models.

    :param tag: the tag of the field's element.
    :param entity: the field's XML mapping, if it has one.
    :param submodels: the models the field holds.
    :param parent: the model that has the field.
    :returns: the tag, qualified if the field is namespaced.
    """
    prefix = entity.ns if entity is not None else None
    for submodel in submodels:
        prefix = prefix or submodel.__xml_ns__
    if not prefix:
        return tag

    namespace_maps = [submodel.__xml_nsmap__ for submodel in submodels]
    namespace_maps.append(parent.__xml_nsmap__)
    for namespace_map in namespace_maps:
        if namespace_map is not None and prefix in namespace_map:
            return f"{{{namespace_map[prefix]}}}{tag}"
    return tag


def _submodels(annotation: object) -> Iterator[type[LibvirtXmlModel]]:
    """Yield the models inside an annotation (unions, lists, ``Annotated``).

    :param annotation: a field's type annotation.
    :returns: the ``LibvirtXmlModel`` classes it contains.
    """
    if isinstance(annotation, type) and issubclass(annotation, LibvirtXmlModel):
        yield annotation
        return

    origin = typing.get_origin(annotation)
    arguments = typing.get_args(annotation)
    if origin is typing.Annotated:
        yield from _submodels(arguments[0])
        return

    if origin in (typing.Union, types.UnionType, list):
        for argument in arguments:
            yield from _submodels(argument)


def _limit(paths: set[str], *, under: str, depth: int | None) -> list[str]:
    """Select the paths below ``under``, down to ``depth`` levels.

    :param paths: the paths to filter.
    :param under: keep this path and the ones below it.
    :param depth: the number of levels below ``under`` to keep, or ``None`` for all.
    :returns: the selected paths, sorted.
    """
    selected = [path for path in paths if path == under or path.startswith(under + "/")]
    if depth is not None:
        base_depth = under.count("/")
        selected = [path for path in selected if path.count("/") - base_depth <= depth]
    return sorted(selected)


if __name__ == "__main__":
    sys.exit(main())
