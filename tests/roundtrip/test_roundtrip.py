"""Round-trip our own samples (``tests/data/<kind>/*.xml``)."""

import tomllib
from pathlib import Path

import pytest

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml.backup import Backup
from libvirtpy.xml.capabilities import StoragePoolCapabilities
from libvirtpy.xml.domain import Domain
from libvirtpy.xml.network import Network
from libvirtpy.xml.nodedev import Device
from libvirtpy.xml.nwfilter import Filter
from libvirtpy.xml.secret import Secret
from libvirtpy.xml.snapshot import Snapshot
from libvirtpy.xml.storage import Pool, Volume
from tests.helpers.xmlcompare import first_difference

DATA_DIR = Path(__file__).parent.parent / "data"
KNOWN_GAPS_FILE = Path(__file__).parent / "known_gaps.toml"

# The sub-directory of tests/data and the model of its files.
SAMPLE_MODELS: dict[str, type[LibvirtXmlModel]] = {
    "domain": Domain,
    "network": Network,
    "pool": Pool,
    "volume": Volume,
    "secret": Secret,
    "filter": Filter,
    "snapshot": Snapshot,
    "nodedev": Device,
    "capabilities": StoragePoolCapabilities,
    "backup": Backup,
}


def _load_known_gaps() -> dict[str, dict[str, str]]:
    with KNOWN_GAPS_FILE.open("rb") as gaps_file:
        gaps: dict[str, dict[str, str]] = tomllib.load(gaps_file)
    return gaps


KNOWN_GAPS = _load_known_gaps()


def _sample_params() -> list[object]:
    params: list[object] = []
    for subdirectory, model in SAMPLE_MODELS.items():
        for path in sorted((DATA_DIR / subdirectory).glob("*.xml")):
            relative = path.relative_to(DATA_DIR).as_posix()
            marks = []
            if relative in KNOWN_GAPS:
                reason = KNOWN_GAPS[relative]["reason"]
                marks.append(pytest.mark.xfail(strict=True, reason=reason))
            params.append(pytest.param(model, path, id=relative, marks=marks))
    return params


def test_every_known_gap_has_a_file_and_a_reason() -> None:
    for relative, gap in KNOWN_GAPS.items():
        assert (DATA_DIR / relative).is_file(), f"{relative}: no such sample"
        assert gap.get("reason"), f"{relative}: gap without a reason"


def test_every_sample_directory_has_a_model() -> None:
    directories = {path.name for path in DATA_DIR.iterdir() if path.is_dir()}

    assert directories == set(SAMPLE_MODELS)


@pytest.mark.parametrize(("model", "path"), _sample_params())
def test_sample_round_trips(model: type[LibvirtXmlModel], path: Path) -> None:
    original = path.read_bytes()

    serialized = model.from_xml(original).to_xml()

    difference = first_difference(original, serialized)
    assert difference is None, difference
