"""Check generated XML against libvirt's RelaxNG schemas.

Round-trip equality alone does not prove that the output is valid: schemas
also constrain element order in places, and builders can produce documents
no sample covers. All tests here need the corpus for the schema files.
"""

from pathlib import Path

import pytest

from libvirtpy.xml._base import LibvirtXmlModel
from tests.helpers.corpus import (
    CORPUS_GROUPS,
    MISSING_CORPUS_MESSAGE,
    SCHEMA_DIR,
    CorpusGroup,
    corpus_params,
    corpus_version,
    schema_path,
)
from tests.helpers.schema import schema_errors
from tests.helpers.xmlcompare import first_difference
from tests.roundtrip.test_roundtrip import SAMPLE_MODELS

DATA_DIR = Path(__file__).parent.parent / "data"

pytestmark = pytest.mark.corpus


def _group_params() -> list[object]:
    params: list[object] = []
    for group in CORPUS_GROUPS:
        for param in corpus_params(group):
            assert isinstance(param, type(pytest.param(None)))
            params.append(
                pytest.param(group, *param.values, id=param.id, marks=param.marks)
            )
    return params


@pytest.fixture
def domain_schema() -> Path:
    if corpus_version() is None:
        pytest.skip(MISSING_CORPUS_MESSAGE)
    return SCHEMA_DIR / "domain.rng"


@pytest.mark.parametrize(("group", "path"), _group_params())
def test_corpus_file_is_valid_input(group: CorpusGroup, path: Path | None) -> None:
    """Checks our corpus manifest: each file must match the schema we pair it with."""
    assert path is not None  # None only in the skipped "no corpus" parameter

    errors = schema_errors(schema_path(group), path.read_bytes())

    assert errors is None, errors


@pytest.mark.parametrize(("group", "path"), _group_params())
def test_corpus_output_is_valid(group: CorpusGroup, path: Path | None) -> None:
    assert path is not None  # None only in the skipped "no corpus" parameter
    if group.model is None:
        pytest.skip(f"{group.schema}: no model yet")
    original = path.read_bytes()
    serialized = group.model.from_xml(original).to_xml()
    if first_difference(original, serialized) is not None:
        pytest.skip("does not round-trip yet")

    errors = schema_errors(schema_path(group), serialized)

    assert errors is None, errors


# The schema each sub-directory of tests/data must validate against.
OWN_SAMPLE_SCHEMAS = {
    "domain": "domain.rng",
    "network": "network.rng",
    "pool": "storagepool.rng",
    "volume": "storagevol.rng",
    "secret": "secret.rng",
    "filter": "nwfilter.rng",
    "snapshot": "domainsnapshot.rng",
    "nodedev": "nodedev.rng",
    "capabilities": "storagepoolcaps.rng",
    "backup": "domainbackup.rng",
}


def _own_sample_params() -> list[object]:
    return [
        pytest.param(model, subdirectory, path, id=f"{subdirectory}/{path.name}")
        for subdirectory, model in SAMPLE_MODELS.items()
        for path in sorted((DATA_DIR / subdirectory).glob("*.xml"))
    ]


@pytest.mark.parametrize(("model", "subdirectory", "path"), _own_sample_params())
def test_own_sample_input_and_output_are_valid(
    model: type[LibvirtXmlModel], subdirectory: str, path: Path
) -> None:
    if corpus_version() is None:
        pytest.skip(MISSING_CORPUS_MESSAGE)
    schema = SCHEMA_DIR / OWN_SAMPLE_SCHEMAS[subdirectory]
    original = path.read_bytes()

    input_errors = schema_errors(schema, original)
    output_errors = schema_errors(schema, model.from_xml(original).to_xml())

    assert input_errors is None, f"the sample itself is invalid: {input_errors}"
    assert output_errors is None, output_errors
