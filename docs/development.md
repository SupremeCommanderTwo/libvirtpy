# Development guide

Conventions for contributors working on `libvirtpy`: one Python package with
three layers. `libvirtpy.xml` has pydantic models that parse and generate libvirt XML
(domain, network, storage, snapshot, ...); `libvirtpy.rpc` speaks the libvirt wire
protocol (standard library only); `libvirtpy.client` offers the operations on top of
both. There is no runtime dependency on libvirt itself.

## Layers

One distribution (`libvirtpy`), three sub-packages and one shared module:

```
src/libvirtpy/
  errors.py   # LibvirtPyError, the base of every error raised on purpose
  xml/        # models; knows nothing of rpc or client
  rpc/        # XDR, session, transports, SASL, events, streams, generated protocol
  client/     # operations, wire adapter, sync/async clients, fake daemon
```

- **Imports point one way:** `client` imports `xml` and `rpc`; `xml` and `rpc` never
  import each other or `client` (only `libvirtpy.errors` is shared).
  `tests/tools/test_layers.py` checks it.
- A rule below that says "the package" without a layer applies to all three.
- Tests: `tests/unit`, `tests/roundtrip`, `tests/schema`, `tests/builder` and
  `tests/data` are for `xml`; `tests/rpc` and `tests/client` for the other layers.
 
## Coding style
 
The goal is code that is readable, easy to maintain and reasonably documented.
Follow the Zen of Python, in particular **"explicit is better than implicit"**.
Prefer boring and obvious over clever and compact.
 
### Readability first
 
- Write code for the next reader. If a line needs a comment to explain *what*
  it does, simplify the line. Comments explain *why*.
- Keep functions small and single-purpose. Extract a well-named helper instead
  of nesting.
- Use descriptive names. No abbreviations except well-known ones (`xml`, `uuid`,
  `mac`, `cpu`). No single-letter names outside tiny comprehensions or loops.
- Flat is better than nested: aim for at most two levels of indentation in a
  function body.
- **Blank lines between steps.** A function reads as a few short paragraphs,
  not a wall of code. When a run of more than five statements (at any nesting
  level) has no blank line, split it where the purpose changes: validate,
  then compute, then emit; a guard clause at the top is its own block, and so
  is the final `return`. One multi-line statement (a call with many arguments,
  a comprehension) counts as one. In tests, separate arrange, act and assert,
  and group the assertions by the object they check.
  `tests/tools/test_code_layout.py` enforces the limit for `src/` and `tools/`.
- **Public first, helpers last.** A module (or class) reads top-down: the public
  API first, then the private helpers (`_name`) that it calls. Move a helper to
  the end of its module, and a private method to the end of its class. The
  exception is a helper that runs at import time (the argument of a decorator,
  a module constant, a class body, `pytest.mark.parametrize`): it must be
  defined above its use. A script keeps its `if __name__ == "__main__":` guard
  last of all. Nested functions (closures) stay where Python needs them.
### Early returns and flat control flow
 
- Handle edge cases and invalid input first, then return or raise. The main
  path stays unindented.
- Avoid long `if/elif/else` chains. For three or more branches, use a dispatch
  `dict`, `match`, or polymorphism (for example a discriminated union of
  models).
- Avoid `else` after `return`, `raise` or `continue`.
```python
# Good
def disk_target_bus(disk: Disk) -> str:
    """Return the bus of ``disk``, falling back to the default for its device kind.

    :param disk: the disk to inspect.
    :returns: the bus name, for example ``"virtio"``.
    :raises ValueError: if the disk has no ``<target>`` element.
    """
    if disk.target is None:
        raise ValueError("disk has no <target>")
    if disk.target.bus is not None:
        return disk.target.bus
    return DEFAULT_BUS_BY_DEVICE[disk.device]


# Bad
def disk_target_bus(disk):
    if disk.target is not None:
        if disk.target.bus is not None:
            return disk.target.bus
        else:
            return DEFAULT_BUS_BY_DEVICE[disk.device]
    else:
        raise ValueError("disk has no <target>")
```
 
### Exceptions
 
- Keep `try` blocks as small as possible: wrap only the single call that can
  raise, never a whole function body.
- Catch specific exceptions. Never use a bare `except:`, and avoid
  `except Exception` unless re-raising or at a top-level boundary.
- No long `try/except` ladders. If several error types need distinct handling,
  split the work into separate functions.
- Do not use exceptions for ordinary control flow when a simple check is clearer.
- Raise library-specific exceptions (subclasses of `LibvirtPyError`) for
  problems callers should handle. Chain with `raise ... from err`.
### Typing
 
- Every function and method has full type annotations, **including the return
  type**. Use `-> None` explicitly when nothing is returned.
- Annotate with precise types. Avoid `Any`; if unavoidable, add a comment saying
  why.
- Use Python 3.14 syntax: `list[str]`, `X | None`, `type Alias = ...` and PEP 695
  generics (`class Box[T]`, `def first[T](...)`). Annotations are evaluated lazily
  (PEP 649), so forward references need no quotes and no
  `from __future__ import annotations`. Do not use `Optional`/`List`/`Dict`/
  `TypeAlias`/`Generic` from `typing`.
- Optional values are `X | None` with an explicit `= None` default. Never
  rely on an implicit default.
- The package ships `py.typed` and must pass `mypy --strict` with no
  suppressions that lack an explanatory comment.
### Explicit over implicit
 
- Prefer explicit imports (`from libvirtpy.xml.domain import Disk`). No
  `from x import *`.
- Define each public module's API with an explicit `__all__`.
- Declare every model field explicitly with its type, default and XML mapping.
  No dynamic attribute generation, metaclass tricks or `setattr` magic.
- Prefer keyword arguments for anything beyond one or two obvious parameters,
  and keyword-only (`*,`) for boolean flags.
- No hidden defaults: if libvirt applies a default when an attribute is
  missing, do not silently fill it in. Keep `None` so that round-tripping XML
  does not change it.
- No mutable default arguments. Use `Field(default_factory=...)`.
- Avoid global state and import-time side effects.
### Documentation (pragmatic)
 
- Every module, class, function and method has a docstring: one summary line,
  plus detail only when behaviour is not obvious. This includes private
  helpers and nested functions (tests are the exception: docstrings are
  optional there).
- For model fields, document the XML element or attribute they map to and
  link the relevant section of the libvirt docs when helpful
  (`https://libvirt.org/formatdomain.html`). A short `Field(description=...)`
  or an inline comment is enough.
- Use reStructuredText (Sphinx) docstrings with field lists. **Every parameter
  has a `:param name:` line** (`self` and `cls` excepted) that says what it
  means, not its type; `**kwargs` says where they go. Add `:returns:` unless the
  summary line already says it, and `:raises:` for every exception the caller
  should expect. Types are not repeated in docstrings, since the annotations
  already carry them. `tests/tools/test_docstrings.py` checks the parameters.
- Do not write docstrings that only repeat the signature: `:param:` lines add
  the meaning, the unit, the allowed values or what happens at the edges.
- Mention the libvirt version that introduced an element when it is known
  ("Since 1.2.8").
### Formatting and tooling
 
- Formatter and linter: `ruff` (format and check). Type checker: `mypy --strict`.
  Tests: `pytest`.
- Line length 88. Imports sorted by `ruff`.
- Run `ruff format`, `ruff check` and `mypy` before finishing any change.
## Project conventions
 
### Project layout
 
Use the `src/` layout so tests always run against the installed package.
 
```
libvirtpy/                   # repository root
  pyproject.toml
  CONTRIBUTING.md
  README.md
  src/libvirtpy/
    py.typed
    errors.py                # LibvirtPyError
    xml/                     # the layer below; paths in this tree are relative to it
     __init__.py              # re-exports the public top-level API
    _base.py                 # shared base model, XML (de)serialization helpers
    _types.py                # shared aliases and enums (UUID, MAC, size units, ...)
    domain/                  # <domain>: one module per area
      __init__.py            # public re-exports, explicit __all__
      domain.py              # Domain (root element)
      storage_source.py      # <source> kinds shared by disk, nvram, mirror, ...
      os.py                  # <os>, <boot>, <nvram>
      cpu.py                 # <cpu>, <vcpu>, <cputune>
      numa.py                # <cpu><numa>, <numatune>
      memory.py              # <memory>, <currentMemory>, <memoryBacking>
      features.py            # <features>
      clock.py               # <clock>, <timer>
      seclabel.py            # <seclabel> (the domain's, not a device source's)
      iothread.py            # <iothreadids>, <defaultiothread>
      blkiotune.py           # <blkiotune>, <throttlegroups>
      launch_security.py     # <launchSecurity>
      sysinfo.py             # <sysinfo> of a domain
      misc.py                # <pm>, <keywrap>, <perf>, <resource>, <idmap>
      qemu.py                # qemu: namespace
      namespaces.py          # vmware:, lxc:, xen:, bhyve: namespaces
      devices/               # <devices> and one module per device kind
        __init__.py
        address.py           # <address> (11 types), shared by every device
        common.py            # <alias>, <boot>, <acpi>, virtio <driver> options
        disk.py              # <disk>, <backingStore>, <mirror>
        interface.py
        graphics.py
        chardev.py           # <serial>, <console>, <parallel>, <channel>
        controller.py
        hostdev.py
        ...                  # audio, filesystem, input, iommu, memballoon, ...
    _shared/                 # models used by more than one document (private)
      network.py             # bandwidth, vlan, virtualport, route, filterref
      storage.py             # secrets, encryption, permissions, SCSI adapter, ...
      sysinfo.py             # SMBIOS groups and entries
      metadata.py            # <metadata>, <cookie>: arbitrary XML kept as text
    network/                 # <network>, <networkport>
    storage/                 # <pool>, <volume>
    snapshot/                # <domainsnapshot>
    backup/                  # <domainbackup>, <domaincheckpoint>
    capabilities/            # read-only: <capabilities>, <domainCapabilities>,
                             #   <storagepoolCapabilities>
    interface/               # a host's <interface> (not a domain device)
    nodedev/                 # <device>, a host device
    nwfilter/                # <filter>, <filterbinding>
    secret/                  # <secret>
    sysinfo.py               # <sysinfo> as a standalone host document
  tests/
    unit/                    # hand-written tests per model
    roundtrip/               # parse -> serialize -> compare, over sample XML
    data/                    # our own sample XML files, one directory per document
    helpers/                 # xmlcompare, corpus manifest, schema validation
    schema/                  # RelaxNG validation and model-vs-schema path checks
  tools/                     # maintenance scripts (not shipped in the package)
    fetch_samples.py         # download libvirt's corpus (pinned version)
    schema_coverage.py       # what the schemas allow that the models do not
    gen_exports.py           # rewrite a package's __init__.py from its modules
```
 
Rules:
 
- **Mirror the libvirt docs.** Module and class names follow the XML element
  names and the section structure of `formatdomain`, so a reader can find the
  model for `<memballoon>` without searching. A model for `<foo>` is `Foo`.
- **One module per cohesive area**, not one per class and not one giant file.
  Split a module when it passes about 400 lines or mixes unrelated elements.
- **Public API vs private.** Anything importable by users is re-exported in a
  package `__init__.py` and listed in `__all__`. Modules starting with `_`
  are private and may change without notice.
- **No import cycles.** Dependencies point one way: `_types`, `_base` and
  `_shared` are imported by everything. The document packages (`domain`,
  `network`, `storage`, `secret`, `nwfilter`, `nodedev`, `interface`,
  `capabilities`) do not import each other: a structure that two of them use
  moves to `_shared` and each package re-exports it. The only exceptions are
  documents that **contain** a domain: `snapshot` and `backup` (its
  checkpoint) import `domain`.
- **`tools/` is not part of the package.** It holds scripts such as the sample
  XML fetcher and any schema-based generator. Nothing in `src/` imports it.
- **Tests mirror the source tree.** The tests for `src/libvirtpy/xml/domain/os.py`
  live in `tests/unit/domain/test_os.py`.
### Packaging
 
- `pyproject.toml` with the `hatchling` build backend. The supported Python
  range is declared in `requires-python`: **3.14 and newer only** (no
  backports, no version checks; `ruff`'s `target-version` and `mypy`'s
  `python_version` are 3.14 too).
- Runtime dependencies are kept minimal: `pydantic` and `pydantic-xml[lxml]`.
  `lxml` is required so users run the same XML backend the tests run.
  Everything else (`pytest`, `ruff`, `mypy`, `lxml-stubs`) is a development
  dependency.
- License: LGPL-2.1-or-later (`LICENSE`): programs that use the library may keep
  their own source closed; changes to the library's own files must be shared.
  The generated protocol code is derived from libvirt's LGPL-2.1+ `.x` files.
- The package version is the single source of truth in `pyproject.toml`.
## Model conventions and XML mapping
 
Models are built on `pydantic-xml`. Behaviour below was verified with
`pydantic` 2.14 and `pydantic-xml` 2.22; re-check these points when upgrading.
 
### Base class
 
- Every model inherits from `LibvirtXmlModel` (in `_base.py`), never directly
  from `BaseXmlModel`. It is the single place for shared config and for the
  fixes below.
- `LibvirtXmlModel.to_xml()` and `to_xml_tree()` default to
  `exclude_none=True`. Without it, `None` attributes are written as empty
  strings (`unit=""`). Do **not** use `skip_empty=True`: it also drops empty
  elements (`<acpi/>`, `<features/>`) and empty attribute values (`x=""`).
- `LibvirtXmlModel` sets `search_mode="unordered"`. pydantic-xml's default
  `strict` mode silently drops children that are not in declaration order
  (and all but the last of interleaved repeated elements), which libvirt XML
  does not guarantee.
- **pydantic-xml's own `unordered` mode reorders same-tag siblings**: it
  consumes a child by swapping it to the front, so reading `<disk>` from
  `[controller0, controller1, disk]` leaves the controllers reversed. Device
  order matters to libvirt. `LibvirtXmlModel.from_xml_tree()` therefore parses
  through `StableXmlElement` (`_xml_element.py`), whose search moves a match
  without disturbing the rest. Regression tests: `tests/unit/test_base.py`.
  The class relies on pydantic-xml internals; re-check it when upgrading.
- pydantic-xml validates parsed XML with `strict=False`, overriding any
  field-level `Strict()`. Reject unwanted input in a validator instead.
- `LibvirtXmlModel.from_xml()`/`from_xml_tree()` default to
  `empty_as_string=True`. With pydantic-xml's default an empty element
  (`<bootloader/>`, `<cmdline></cmdline>`) reads as `None` and is lost on a
  round trip. Consequence: element text that may be missing on a model with
  attributes (`<loader readonly='yes'/>`) must be `value: OptionalText = None`,
  which turns `""` into `None`.
- `lxml` is a required runtime dependency (pydantic-xml would otherwise fall
  back to the standard library `etree`, an untested path). Overrides of
  pydantic-xml methods annotate with `pydantic_xml.element.native.etree`,
  which pydantic-xml declares with the standard library types.
- Models are **mutable** (users build and edit configurations) and use
  `validate_assignment=True`.
### Mapping elements and attributes
 
- Attribute: `attr()`. Child element: `element()`. Text content: a plain
  field named `value` with no `attr()`/`element()`, declared with
  `Field(description="Element text: ...")`.
- **Output order.** Fields are written in declaration order, and a base class's
  fields come before the subclass's. Parsing ignores the order of different
  tags, but libvirt's schemas often require one (`<value>` before `<enum>` in
  `<loader>` of domain capabilities). The schema tests (`pytest -m corpus`)
  catch this; when a base class gets the order wrong, declare the fields in
  the subclass instead. Where libvirt interleaves two lists (`<model>` and the
  `<blockers>` of that model), keep two lists and write them interleaved with
  `@xml_field_serializer` (see `CustomMode`).
- When the same tag means different things in different parents, prefix the
  class with the parent: `<acpi>` in `<os>` is `OsAcpi`, `<cache>` in a NUMA
  cell is `NumaCache`.
- Python field names are `snake_case`; the XML name is always given explicitly
  (`tag="currentMemory"`, `name="bus"`) whenever it differs from the field name.
  Do not rely on implicit renaming.
- Repeated elements are `list[T]` with `default_factory=list`. The field
  name is plural, the XML tag is explicit: `disks: list[Disk] = element(tag="disk", ...)`.
- Every field not required by libvirt is `X | None = None` (or an empty list).
  A missing element or attribute stays `None`; we never invent a value.
### Variants (`<disk type='file'>` vs `type='network'`)
 
- Use **one model per variant**, with the discriminator as a `Literal`
  attribute, and a **plain union** of them:
```python
Disk = FileDisk | NetworkDisk | BlockDisk
disks: list[Disk] = element(tag="disk", default_factory=list)
address: Address | None = element(tag="address", default=None)
```

  Do **not** use `Annotated[..., Field(discriminator="type")]` with
  pydantic-xml 2.22: serializing a `None` discriminated field crashes, and in
  a list an element with an unknown `type` is silently dropped together with
  every element after it. With a plain union the literals make exactly one
  variant match and an unknown value is a validation error (tested in
  `tests/unit/domain/devices/test_controller.py`). Re-check when upgrading.
- Fields shared by all variants live in a private base class
  (`_ControllerBase`); each variant adds its `type` literal and own fields.
- When the discriminator is on the **parent** and the child has none (the
  `<source>` of `<disk type='file'>` vs `type='block'`), use **storage
  mixins**: one small mixin per `type` (`FileStorage`: the `type` literal and
  the matching `source`), combined with a parent base class
  (`class FileDisk(_DiskBase, FileStorage, tag="disk")`). Disk, backing store,
  mirror, data store and NVRAM share the mixins of
  `domain/storage_source.py`. A missing `type` means `file`, so `FileStorage`
  has `type: Literal["file"] | None`.
- Variants of one element that differ only by optional children and
  attributes of the *same* structure (`NetworkSource` for all `protocol`s)
  are one model; libvirt, not the model, checks which combinations are valid.
- A union that contains itself (`<backingStore>` in `<backingStore>`, or
  `<source>` <-> `<dataStore>`) needs forward references and a
  `model_rebuild()` of **every** class in the cycle after all of them exist
  (see the end of `storage_source.py` and `devices/disk.py`); otherwise
  pydantic-xml fails with "model X is partially initialized".
- A sub-model used under several tags (`<input>`/`<output>` streams of
  `<audio>`) has no tag of its own; the field gives it with `element(tag=)`.
- Use a single model with optional fields only when variants differ by one or
  two fields and share the rest, or when the variant is chosen by element
  *text* (`<os><type>hvm</type>`), which a discriminated union cannot
  dispatch on. Say why in the module docstring.
- An unknown discriminator value is a validation error, not a silent fallback.
### Booleans: `yes`/`no`, `on`/`off`
 
- Define shared annotated types in `_types.py` (`YesNo`, `OnOff`) that
  convert to and from `bool`, with an explicit serializer. Libvirt uses
  both; each field uses the one the schema specifies. They accept only their
  two words (or a `bool`); `"true"`, `"1"` or the other pair are errors.
- Keep `None` for "not set". Do not turn it into `False`.
### Presence flags (`<acpi/>`, `<apic/>`)
 
- A plain `bool` element field does **not** work: `<acpi/>` parses as `False`
  and serializes as `<acpi>true</acpi>`. A `bool` with a custom serializer
  does not work either: an empty element is read as missing, and
  `exclude_none` checks the value before the serializer runs.
- Use the shared empty model `PresenceFlag` from `_types.py`, as
  `acpi: PresenceFlag | None = element(tag="acpi", default=None)`. `None`
  means absent; `PresenceFlag()` writes `<acpi/>`. This relies on
  `exclude_none=True` (see Base class).
- An element that is a flag *plus* optional attributes (`<apic eoi='on'/>`,
  `<hap state='off'/>`) is its own small model with optional attributes;
  `FeatureState` covers the common `state='on|off'` case.
### Units and sizes
 
- Keep the value and its unit exactly as in the XML: `Memory(value=4, unit="GiB")`.
  No automatic conversion on parse or serialize; that would change the document
  on a round trip.
- `unit` is `SizeUnit` (from `_types.py`), defaulting to `None`. It is a
  `str` checked against the schema's pattern, not a `Literal`: the schema
  accepts units case-insensitively (`kib`, `KiB`, `k`, `KB`, `bytes`...).
  Libvirt's default (usually KiB) applies when it is `None`.
- Conversion is an explicit helper, for example `memory.to_bytes() -> int`.
### Enums and constrained values
 
- Use `str`-based `Enum`/`Literal` for closed sets that libvirt documents
  (`bus`, `device`, `cache`, ...). Use `str` where libvirt accepts free text or
  where the set grows between versions (machine types, CPU models).
- Enum member names are `UPPER_SNAKE_CASE`; values are the exact XML strings.
- Never use integer `Literal`s (`Literal[1, 2, 3]`): parsed values are strings
  and pydantic does not coerce them to integer literals. Use
  `int` with `ge=`/`le=` instead.
- Mirror the schema's numeric ranges (`unsignedInt` -> `ge=0`,
  `positiveInteger` -> `ge=1`) and patterns.
### Unknown elements and attributes
 
- The default is `extra="ignore"` (like the Go library), so we can parse XML
  produced by newer libvirt versions.
- Findings that shape the rules: the `extra` setting of the **root** model
  applies to the whole tree, and `forbid` rejects unknown *attributes* but
  not unknown *child elements*. `allow` does not preserve extras on output.
- Therefore unknown data is never "kept"; it is detected. The round-trip
  tests compare input and output XML (see Testing) and fail on any loss.
  Tests may use a root subclass with `extra="forbid"` to catch unknown
  attributes early.
### Namespaces
 
- The `qemu:` namespace (`<qemu:commandline>`, ...) and similar extensions are
  modelled in a separate module (`domain/qemu.py`; `domain/namespaces.py` for
  `vmware:`, `lxc:`, `xen:`, `bhyve:`) and wired into `Domain` explicitly.
  They are not part of the core model.
- A namespaced model sets `ns="qemu"` and `nsmap={"qemu": URI}`; its field in
  `Domain` repeats `ns=` and `nsmap=`. This declares the namespace on the
  element that uses it, not on every `<domain>` root, and the prefix resolves
  when parsing. Child elements inherit the namespace from their model.
- Prefixes are not kept: `<my:data xmlns:my=...>` may come back as
  `<ns0:data xmlns:ns0=...>`. The XML is equivalent.
### Arbitrary content (`<metadata>`)
 
- pydantic-xml cannot capture children of unknown name. `Metadata.elements`
  holds one XML string per child; `@xml_field_validator` and
  `@xml_field_serializer` read and write them, and the field has a placeholder
  `element(tag=...)` that is never used (pydantic-xml needs a mapping to build
  the class). Comments and whitespace between the children are not kept.
### Validation scope
 
- Models check **structure and types**. They do not re-implement libvirt's
  semantic rules (valid machine/CPU combinations, device limits); libvirt
  reports those.
- Cross-field checks are allowed only for rules stated in the schema, as
  `model_validator`s with a clear error message.
## Testing
 
The library's value is faithful XML handling, so tests are mostly about
**not losing data**. Run with `pytest`; keep the suite fast and offline.
 
### Test kinds
 
1. **Unit tests** (`tests/unit/`): small, hand-written tests per model and
   shared type. Cover: parsing a minimal element, serializing a built model,
   `None` handling, `YesNo`/`OnOff`, units, enum values, discriminated-union
   dispatch, and the error for an unknown discriminator.
2. **Round-trip tests** (`tests/roundtrip/`): for each sample XML file, parse it
   with the model, serialize it, and compare with the original. This is the
   main safety net, and the way to find unmodelled elements and attributes.
3. **Schema validation tests** (`tests/schema/`): validate serialized output
   against libvirt's RelaxNG schemas (`src/conf/schemas/*.rng` in the corpus)
   with `lxml`. This proves we *generate* valid XML, which round-trip equality
   alone does not. They also check that every path our models read or write
   exists in the schema (catches wrong tag or attribute names).
4. **Builder tests**: a few end-to-end examples that build a `Domain` in
   Python and compare the result with an expected XML file.
### Sample data
 
- The primary corpus is the XML under libvirt's own `tests/` directory, as the
  Go library uses.
- Do not copy libvirt's files into this repository (they are LGPL-licensed
  and large). `tools/fetch_samples.py` downloads the official release tarball
  of a **pinned libvirt version** (`LIBVIRT_VERSION`, with its SHA-256) and
  extracts the XML samples and schemas into `.cache/libvirt/` (untracked).
  Updating the version is a deliberate, reviewed change: check the new
  tarball's GPG signature before pinning its hash.
- `tests/helpers/corpus.py` lists the corpus groups (directory -> schema ->
  root model). It mirrors libvirt's `tests/virschematest.c` for the pinned
  version; re-check it when updating. A group gets its `model` when the root
  model exists. Files named `*-invalid.*` (libvirt's negative tests) and
  broken XML are excluded.
- Run `python tools/gen_exports.py libvirtpy.xml.<package>` after adding a public
  class: it rewrites the package `__init__.py` from the modules' `__all__`.
  `--extra module:Name,Name` re-exports names from `_shared`.
- `tools/schema_coverage.py <root>` (`domain`, `network`, `pool`, `volume`,
  `snapshot`, ...; see `ROOT_MODELS`) lists the schema paths (elements and
  attributes)
  not modelled yet, e.g. `--under /domain/devices/disk`. It reads pydantic-xml
  internals (`extract_field_xml_entity_info`); re-check it when upgrading.
  Both sides (schema and models) expand a recursive structure once: an
  element that is already its own ancestor is not expanded again.
- Tests that need the corpus are marked `@pytest.mark.corpus` and skip with a
  clear message if the cache is absent. The default `pytest` run still passes
  offline using only `tests/data/`, which holds a small set of our own
  hand-written files (owned by this project).
### Comparison rules
 
Compare **normalized trees**, not strings. Normalization ignores:
 
- whitespace between elements and comments;
- attribute order and quote style;
- the order of children **with different tags**.
It does **not** ignore the order of siblings with the same tag (device order
can matter to libvirt) or any difference in attribute values or text.
The comparison lives in one helper, `tests/helpers/xmlcompare.py`, and reports
readable paths to the differences (`/domain/devices/disk[2]/@bus`).
 
### Known gaps
 
- Our own sample files (`tests/data/`) that do not yet round-trip are listed
  in `tests/roundtrip/known_gaps.toml`, each with a path to the first
  difference and a reason ("`<vcpus>` not modelled yet").
- Listed files are marked `xfail(strict=True)`: when a gap is fixed, the test
  fails until the entry is removed, so the list only shrinks.
- A new gap is never added without a reason. Adding models is preferred over
  adding entries.
- The libvirt corpus is **not** listed there while coverage is low. The corpus
  run (`pytest -m corpus -q --tb=no -rN`) prints the share of files that
  round-trip and ranks the differences by number of files affected
  (`CORPUS_TOP=500` prints more); that ranking decides what to model next. It is not a hard threshold. Once the
  share is high (about 80%), switch the corpus to per-file known gaps too.
### Style of tests
 
- Names state the behaviour: `test_disk_without_bus_keeps_bus_none`.
- One behaviour per test; use `pytest.mark.parametrize` for variations.
- Use real XML in tests, not mocks. There is nothing to mock: the library has
  no I/O.
- The code style rules above apply to tests too, except that docstrings are
  optional.
- Every bug fix comes with a test that fails without the fix.
### Quality gates (CI)
 
Required on every change: `ruff format --check`, `ruff check`, `mypy --strict`,
and `pytest` (default run, offline; `pyproject.toml` deselects `corpus`). The
corpus run (`-m corpus`) runs in a separate CI job against the pinned libvirt
version; its round-trip failures are expected while coverage grows, but the
schema tests in it must pass. Line coverage is reported but
not gated.
 
### Documentation

- `docs/` is a Sphinx project (furo theme, MyST Markdown guides, autodoc reference built
  from the reStructuredText docstrings), published by Read the Docs
  (`.readthedocs.yaml`). Build it with `python -m sphinx -b html docs docs/_build/html`;
  it must build without warnings.
- A class re-exported by several packages is documented once (`docs/conf.py`).
- A new public document package or client feature gets a line in the guide and, for
  models, an `automodule` in `docs/reference/`.

## Still to define
 
The release process.
 

## Client (`libvirtpy.client`)

The client speaks to libvirt daemons in the library's models, over the real
wire protocol (pure Python) or against the in-memory `FakeLibvirt`.

- **Layers.** the `operations/` package (one module per resource, helpers in `_common.py`) holds all the logic as sans-I/O generators: they
  `yield` a `Request(procedure, arguments)` and receive the reply. `_runner.py`
  drives them synchronously or asynchronously. `xml` never imports `client`.
- **Thin clients.** `client.py` and `aio.py` are **generated** by
  `tools/gen_client.py` from the operation modules: one one-line method per operation,
  and one proxy class per reference kind (`client.domain(ref).set_vcpus(4)`).
  Never edit them by hand; change the operation modules, run `tools/gen_exports.py libvirtpy.client.operations` if you added a function, then regenerate.
  `tests/tools/test_gen_client.py` fails on drift.
- **References.** A reference is an id (`int`), a name, a UUID (`UUID`, or text
  that looks like one) or a model; `references.py` turns it into the lookup request.
- **Fake daemon.** the `client/testing/` package (`FakeLibvirt`) is a test double and follows the exemptions of
  tests (docstrings and layout are not checked). Examples in `examples/` run as
  tests (`tests/client/test_examples.py`).

### Wire protocol

- `rpc/protocol/types.py` and `procedures.py` are **generated** by
  `tools/gen_protocol.py` from libvirt's `.x` files (`tools/fetch_samples.py`
  keeps them in `.cache/libvirt`). Never edit them; the generated files are
  committed, and `pytest -m corpus` checks that they are up to date.
- `rpc/xdr.py` is the hand-written XDR codec; the generated dataclasses
  describe their layout in `xdr_fields`. `tools/xdr_parser.py` parses the `.x`
  files. Field names are snake_case (`callbackID` -> `callback_id`).
- The daemon that serves a procedure (`Procedure.driver`) is a port of
  `get_conn_method` of libvirt's `gendispatch.pl`.
- **Layers of the wire.** `rpc/session.Session` (no I/O: framing, serials, errors,
  keepalive) is moved by `rpc/sync.SyncRpc` or `rpc/aio.AsyncRpc`. `rpc/sockets.py`
  finds and authenticates the daemon sockets (modular daemons first, then
  `libvirtd`); `wire.py`/`wire_aio.py` turn an operation's `Request` into the
  generated argument struct and the reply back into handles, text and numbers.
- **Requests use real names.** `Request.procedure` is a `Procedure.name` and the
  argument keys are the struct's fields; the fake daemon and
  `tests/client/test_requests_match_protocol.py` enforce it.
- **Live tests.** `pytest -m libvirt` talks to the daemon of the machine and
  only reads; it skips if none is reachable. Real data is the best test of the
  models: when libvirt's output disagrees with its own schema, the model follows
  the daemon (see `UsbDeviceCapability.port`) and a unit test records it.
- **Remote hosts.** `rpc/uri.py` parses the URI; `rpc/remote.py`/`remote_aio.py`
  connect over `ssh` (a child process running `virt-ssh-helper` or `nc -U`), TLS
  (client certificate, then the daemon's one acceptance byte) or plain TCP. A
  remote host is one connection for all drivers (`REMOTE_KEY`), opened with the
  URI without transport and host. `tests/helpers/fake_rpc_server.py` is a real
  RPC server for tests; remote tests use it over TCP, TLS (certificates made
  with `openssl`) and a fake `ssh` script. The automated tests never
  reach a real remote host; SSH, TLS and TLS+SASL (SCRAM) were checked by hand against a
  real libvirt 12 server prepared with `tools/setup_test_vps.sh`, and that run found
  bugs the fake server could not (the unquoted `sh -c` over ssh, the comma-separated
  SASL mechanism list, the silent system-CA fallback of a missing `pkipath`). When
  you change a transport, repeat that check with `examples/real/03_ssh.py`, `04_tls.py`
  and `05_tls_with_sasl.py`, and make the fake server behave like what it exposed.
- **SASL.** `rpc/sasl.py` implements SCRAM-SHA-256/1, DIGEST-MD5 and PLAIN with the
  standard library only; `sasl_exchange` is I/O-free and driven by both clients
  (`sockets.authentication` picks none, polkit or SASL). There is no SASL
  security layer, so SASL is refused on plain TCP and used only on UNIX
  sockets, TLS and SSH. GSSAPI is not supported. Mechanisms are tested against
  the RFC vectors (2831, 5802, 7677) and a SCRAM/PLAIN fake server.
- **Generated clients are exempt from the 400-line module guideline.**

### Operations (the client's API)

- **One module per area** in `client/operations/` (`domain_lifecycle`, `domain_tuning`,
  `domain_block`, `network_port`, `storage_info`, `host`, ...). Each has an explicit
  `__all__`; run `tools/gen_exports.py libvirtpy.client.operations` after adding a
  function, then `tools/gen_client.py`. `_common.py` holds the helpers (`on_domain`,
  `on_network`, ..., `get_typed_parameters`, the `as_*` reply checks).
- **Docstring lines of an operation stay within 84 columns**: the generated client
  methods indent them by four more.
- **Replies.** A reply of one field is unwrapped (a field named `ret` is a count
  and dropped); a typed-parameter list becomes a `dict`; an object becomes a
  `Handle`. A reply of several fields is the generated return struct
  (`DomainGetBlockInfoRet`...), documented in the operation. Common ones with a
  friendlier form are in `client/types.py` (`JobStats`, `VcpuStatus`).
- **Typed parameters** (`rpc/typed_params.py`): a `dict` in Python. The integer
  width of each documented name comes from libvirt's headers
  (`tools/gen_typed_params.py` -> `protocol/typed_hints.py`); other names are typed
  from the value. Getters make libvirt's two calls (count, then values).
- **Flags** are plain `int`s; the docstring names the libvirt enum. Typed
  `IntFlag`s are not generated yet.
- **Tests of operations.** `test_operations_speak_the_protocol.py` runs *every*
  public operation with sample arguments through `tests/helpers/synthetic_daemon.py`,
  which checks the request against the real argument struct (names, XDR types,
  limits) and answers with a sample of the real return struct.
  `test_protocol_coverage.py` makes each of the 456 procedures either used,
  superseded by one that is used, or listed as not supported with the reason
  (file descriptors; events and migration steps are handled separately). `tests/live/` checks the
  read-only operations against a real daemon.
- **The in-memory `FakeLibvirt` serves only the first operations** (domains,
  networks, pools, volumes, snapshots, secrets, filters, interfaces, devices); the
  others raise `NotSupportedError` there. Test new operations with the synthetic
  daemon and, for reads, the live tests.
- **Not supported:** file-descriptor passing (`open_graphics`, the `*_with_files`
  calls), and *starting* a migration (the `migrate_*3` steps are coordinated by the
  client between two daemons).
- **Write tests on a real daemon** (`pytest -m libvirt_write`, never in the default
  run): they create, change and remove throwaway `lvxtest-*` domains, networks,
  pools, volumes, secrets and filters on `qemu:///system`. `tests/live/scratch.py`
  registers every object and removes only registered objects whose name has the
  prefix; each test fails if anything is left (objects or `/var/tmp/lvxtest-*`).
  Keep disks to a few MiB. On an SELinux host (enforcing), qemu may only create
  sockets in `/run/libvirt/qemu` and files root made in `/var/tmp` cannot be
  deleted by the user: delete them through a pool volume (`delete_pool_volume`).

### Events and streams

- **Events.** `Session` decodes every pushed message whose procedure has a
  `message` struct (the generator links `remote_<procedure>_msg`) into a
  `ServerEvent`. `SyncRpc` has a reader thread (it also answers keepalive pings
  and lets several threads call at once); `AsyncRpc` does the same in its loop.
  `client.events(source, kinds, target=...)` returns a `Subscription` /
  `AsyncSubscription` (`rpc/events.py` has the `Event`, the kinds and sources). A
  registration passes `on_result=` so the listener exists before the first event
  can arrive. A connection loss ends a subscription with `ConnectionLostError`.
- Events work only on a real daemon connection (the fake raises `NotSupportedError`).
  `tests/client/test_events.py` uses the fake RPC server (it can push events
  and pings); `tests/live/` receives real lifecycle events from qemu.
- **Streams.** A call with `Request(..., stream="read"|"write"|"both")` returns an
  open `RemoteStream` (a real `io.RawIOBase`: `read`, `write`, `with`, `shutil.copyfileobj`)
  or, for the async client, an `AsyncRemoteStream`; `tools/gen_client.py` rewrites the
  type for the async methods. The stream has the serial of the call. libvirt's wire
  rules, found with the real daemon: data is a `STREAM` packet with status `CONTINUE`;
  **an empty `CONTINUE` is end of data** (not `OK`); the finishing side sends `OK` and
  the daemon answers `OK`; the client gives up with `ERROR`. A stream's receiver stays
  registered until `closed` or `error`. A stream we were still reading is aborted on
  `close()`; one at its end, or one we write, is finished and confirmed.
- **Debugging a hang:** run it under `faulthandler.dump_traceback_later(n, exit=True)`
  *inside a `try/finally` that cleans up*; a killed script leaves `lvxtest-*` objects
  (the write tests list and remove them: `Scratch.leftovers()`).

### Coverage and quality gates

- `mypy --strict` runs inside the default `pytest` run (`tests/tools/test_types.py`, about
  2 s), so a type error fails locally exactly as it does in CI.
- `pytest --cov` must stay at 95% or more (`[tool.coverage.report] fail_under`); the
  default run covers about 98%. Generated code is covered too: `tests/client/
  test_generated_clients.py` calls every generated client method and proxy, sync and
  async, and checks it sends exactly the requests of its operation.
- Ruff runs `E F W I UP B SIM RET N A RUF PERF ARG PIE PLW2901`. A hook with a fixed
  signature (pydantic-xml, a protocol method, a Sphinx hook) gets a `noqa` that says why;
  an unused argument elsewhere is a smell: remove it or name it `_`.

### Robustness

- **Keepalive and timeouts.** `ConnectionOptions` (`rpc/options.py`) travels from
  `open()` down to `SyncRpc`/`AsyncRpc`. A keepalive thread/task pings after
  `keepalive_interval` of silence and fails the connection after
  `keepalive_interval * (keepalive_count + 1)`; the real daemon answers a `PING` with
  a `PONG` even before anything is enabled (checked live). `call_timeout` is off by
  default (some calls are slow). A timed-out or cancelled call is *abandoned*
  (`Session.abandon`): its late reply is dropped instead of killing the connection.
- **Reconnect** (`reconnect=True`, `ConnectionOptions.reconnect_attempts`): the
  transports (`WireTransport`, `AsyncWireTransport`) replace a channel whose
  `rpc.failure` is set, with the waits of `reconnect_waits()`; a call that was in
  flight is never repeated (it may have run), `AuthFailedError` is not retried, and
  subscriptions are registered again by `_restore` (a thread / a task). Streams are not
  resumed. `RunningServer.drop_connections()` and `.close()` make tests of this.
- **Bounded queues.** A subscription keeps at most `max_events` (`EventBuffer`); the
  oldest event is dropped and counted in `dropped`. Never add an unbounded queue
  between the daemon and the user.
- **Hostile input.** Whatever the daemon sends, only `LibvirtPyError`s may come out
  (`tests/rpc/test_fuzz.py`, seeded random bytes and mutated valid packets, for every
  procedure). New decoders (SASL messages, URIs, XDR types) get a case there.
- `tests/helpers/fake_rpc_server.py` can stay silent (`silent`), answer late
  (`delayed`) or ignore pings (`answer_pings`) to test these.

### Round-tripping real daemon XML

- The corpus proves the models on libvirt's own test files; `tests/live/` proves them on
  what a daemon actually writes. `test_live_roundtrip.py` (`-m libvirt`, read-only)
  parses and rewrites every domain (7 flag variants), snapshot, network, pool, volume,
  host device, filter, interface, secret and capability document of the host and
  compares the trees. `test_live_write.py` (`-m libvirt_write`) does the same for a
  running VM with ~20 device kinds, a network with a port, a checkpoint, a backup job,
  external snapshots, and for unusual features (TPM, UEFI with NVRAM, CPU/NUMA/memory
  tuning, SELinux labels, hot-plug memory). Big XML lives in `tests/live/xml_fixtures.py`.
- **Findings so far:** the daemon omits `<port>` of a USB root hub (the schema requires
  it) and adds `index` to the disks of a running backup (the schema lacks it). The model
  follows the daemon, a unit test records why, and an entry in
  `KNOWN_SHARED_MODEL_EXTRAS` (`tools/schema_coverage.py`) tells the schema test the
  extra path is intended.
