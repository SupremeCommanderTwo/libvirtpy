"""The libvirt sample corpus: which files exist and which schema covers them.

The groups mirror libvirt's own ``tests/virschematest.c`` for the pinned
version, so every file is checked against the schema libvirt checks it
against. Download the corpus with ``python tools/fetch_samples.py``.

Excluded from the corpus:

- files named ``*-invalid.*``: libvirt's negative tests, expected to fail
  schema validation (``virschematest.c`` treats them that way);
- files that are not well-formed XML (``virschematest.c`` skip lists).
"""

from dataclasses import dataclass
from pathlib import Path

import pytest

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

__all__ = [
    "CORPUS_DIR",
    "CORPUS_GROUPS",
    "CorpusGroup",
    "CorpusSource",
    "corpus_files",
    "corpus_params",
    "corpus_version",
    "schema_path",
]

CORPUS_DIR = Path(__file__).resolve().parents[2] / ".cache" / "libvirt"
SCHEMA_DIR = CORPUS_DIR / "src" / "conf" / "schemas"
MISSING_CORPUS_MESSAGE = (
    f"libvirt corpus not found in {CORPUS_DIR}; run: python tools/fetch_samples.py"
)

# Marks libvirt's negative test files; see virschematest.c.
INVALID_MARKER = "-invalid."


@dataclass(frozen=True)
class CorpusSource:
    """XML files in one corpus directory (not recursive, like virschematest)."""

    directory: str
    pattern: str = "*.xml"
    skip: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CorpusGroup:
    """Corpus files that libvirt validates against one RelaxNG schema."""

    schema: str
    sources: tuple[CorpusSource, ...]
    model: type[LibvirtXmlModel] | None
    """The root model for these files, or ``None`` while not modelled yet."""


def _sources(*directories: str) -> tuple[CorpusSource, ...]:
    return tuple(CorpusSource(directory) for directory in directories)


CORPUS_GROUPS = (
    CorpusGroup(
        schema="domain.rng",
        model=Domain,
        sources=(
            CorpusSource("tests/domainschemadata"),
            CorpusSource(
                "tests/qemuxmlconfdata",
                skip=frozenset({"broken-xml-invalid.xml"}),
            ),
            *_sources(
                "tests/xmconfigdata",
                "tests/lxcxml2xmldata",
                "tests/lxcxml2xmloutdata",
                "tests/bhyvexml2argvdata",
                "tests/bhyvexml2xmloutdata",
                "tests/genericxml2xmlindata",
                "tests/genericxml2xmloutdata",
                "tests/xlconfigdata",
                "tests/libxlxml2domconfigdata",
                "tests/qemuhotplugtestdomains",
            ),
            CorpusSource("examples/xml/test", pattern="testdom*.xml"),
            *_sources(
                "tests/qemuhotplugtestcpus",
                "tests/securityselinuxlabeldata",
                "tests/domainconfdata",
                "tests/lxcconf2xmldata",
                "tests/qemumemlockdata",
                "tests/vmx2xmldata",
                "tests/xml2vmxdata",
                "tests/bhyveargv2xmldata",
                "tests/qemuagentdata",
                "tests/chxml2xmlin",
                "tests/chxml2xmlout",
            ),
        ),
    ),
    CorpusGroup(
        schema="capability.rng",
        model=Capabilities,
        sources=_sources(
            "tests/capabilityschemadata",
            "tests/vircaps2xmldata",
            "tests/qemucaps2xmloutdata",
        ),
    ),
    CorpusGroup(
        schema="domaincaps.rng",
        model=DomainCapabilities,
        sources=_sources("tests/domaincapsdata"),
    ),
    CorpusGroup(
        schema="domainbackup.rng",
        model=Backup,
        sources=_sources("tests/domainbackupxml2xmlin", "tests/domainbackupxml2xmlout"),
    ),
    CorpusGroup(
        schema="domaincheckpoint.rng",
        model=Checkpoint,
        sources=_sources(
            "tests/qemudomaincheckpointxml2xmlin",
            "tests/qemudomaincheckpointxml2xmlout",
        ),
    ),
    CorpusGroup(
        schema="domainsnapshot.rng",
        model=Snapshot,
        sources=_sources(
            "tests/qemudomainsnapshotxml2xmlin",
            "tests/qemudomainsnapshotxml2xmlout",
        ),
    ),
    CorpusGroup(
        schema="interface.rng",
        model=HostInterface,
        sources=_sources("tests/interfaceschemadata"),
    ),
    CorpusGroup(
        schema="network.rng",
        model=Network,
        sources=(
            CorpusSource(
                "tests/networkxmlconfdata",
                skip=frozenset(
                    {
                        "nat-network-dns-srv-record-domain-newline.xml",
                        "nat-network-dns-srv-record-target-newline.xml",
                        "nat-network-dns-txt-recor-record-newline.xml",
                    }
                ),
            ),
            CorpusSource("examples/xml/test", pattern="testnet*.xml"),
            *_sources("tests/networkxml2xmlupdateout", "tests/networkxml2firewalldata"),
        ),
    ),
    CorpusGroup(
        schema="networkport.rng",
        model=NetworkPort,
        sources=_sources("tests/virnetworkportxml2xmldata"),
    ),
    CorpusGroup(
        schema="nodedev.rng",
        model=Device,
        sources=(
            *_sources("tests/nodedevschemadata", "tests/nodedevxml2xmlout"),
            CorpusSource("examples/xml/test", pattern="testdev.xml"),
        ),
    ),
    CorpusGroup(
        schema="nwfilter.rng",
        model=Filter,
        sources=_sources(
            "tests/nwfilterxml2xmlout",
            "src/nwfilter/xml",
            "tests/nwfilterxml2xmlin",
            "tests/nwfilterxml2firewalldata",
        ),
    ),
    CorpusGroup(
        schema="nwfilterbinding.rng",
        model=FilterBinding,
        sources=_sources("tests/virnwfilterbindingxml2xmldata"),
    ),
    CorpusGroup(
        schema="secret.rng",
        model=Secret,
        sources=_sources("tests/secretxml2xmlin"),
    ),
    CorpusGroup(
        schema="storagepoolcaps.rng",
        model=StoragePoolCapabilities,
        sources=_sources("tests/storagepoolcapsschemadata"),
    ),
    CorpusGroup(
        schema="storagepool.rng",
        model=Pool,
        sources=(
            *_sources(
                "tests/storagepoolxml2xmlin",
                "tests/storagepoolxml2xmlout",
                "tests/storagepoolschemadata",
            ),
            CorpusSource("examples/xml/storage", pattern="pool-*.xml"),
            CorpusSource("examples/xml/test", pattern="testpool.xml"),
        ),
    ),
    CorpusGroup(
        schema="storagevol.rng",
        model=Volume,
        sources=(
            *_sources(
                "tests/storagevolxml2xmlin",
                "tests/storagevolxml2xmlout",
                "tests/storagevolschemadata",
            ),
            CorpusSource("examples/xml/storage", pattern="vol-*.xml"),
            CorpusSource("examples/xml/test", pattern="testvol.xml"),
        ),
    ),
    CorpusGroup(
        schema="sysinfo.rng",
        model=Sysinfo,
        sources=_sources("tests/sysinfodata"),
    ),
)


def corpus_version() -> str | None:
    """Return the libvirt version of the downloaded corpus, or ``None``."""
    version_file = CORPUS_DIR / "VERSION"
    if not version_file.is_file():
        return None
    return version_file.read_text(encoding="utf-8").strip()


def schema_path(group: CorpusGroup) -> Path:
    return SCHEMA_DIR / group.schema


def corpus_files(group: CorpusGroup) -> list[Path]:
    """Return the valid sample files of ``group``, sorted by path."""
    files: list[Path] = []
    for source in group.sources:
        for path in sorted((CORPUS_DIR / source.directory).glob(source.pattern)):
            if path.name in source.skip or INVALID_MARKER in path.name:
                continue
            files.append(path)
    return files


def corpus_params(group: CorpusGroup) -> list[object]:
    """Return one ``pytest.param`` per file of ``group``, with readable ids.

    Without a downloaded corpus this is a single skipped parameter, so the
    test reports how to get the corpus instead of silently not running.
    """
    if corpus_version() is None:
        skip = pytest.mark.skip(reason=MISSING_CORPUS_MESSAGE)
        return [pytest.param(None, id="no-corpus", marks=skip)]
    return [
        pytest.param(path, id=path.relative_to(CORPUS_DIR).as_posix())
        for path in corpus_files(group)
    ]
