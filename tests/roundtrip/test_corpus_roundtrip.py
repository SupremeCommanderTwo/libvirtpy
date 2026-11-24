"""Round-trip every corpus file that has a model.

The terminal summary (see ``tests/conftest.py``) prints the share of files
that round-trip and ranks what is missing, to decide what to model next.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from libvirtpy.xml._base import LibvirtXmlModel
from tests.helpers.corpus import CORPUS_GROUPS, corpus_params
from tests.helpers.xmlcompare import differences

# The summary hook reads results stored under these user properties.
DIFFERENCES_PROPERTY = "roundtrip_differences"
SCHEMA_PROPERTY = "roundtrip_schema"


def _params() -> list[object]:
    params: list[object] = []
    for group in CORPUS_GROUPS:
        if group.model is None:
            continue
        for param in corpus_params(group):
            assert isinstance(param, type(pytest.param(None)))
            params.append(
                pytest.param(
                    group.schema,
                    group.model,
                    *param.values,
                    id=param.id,
                    marks=param.marks,
                )
            )
    return params


@pytest.mark.corpus
@pytest.mark.parametrize(("schema", "model", "path"), _params())
def test_corpus_file_round_trips(
    schema: str,
    model: type[LibvirtXmlModel],
    path: Path | None,
    record_property: Callable[[str, object], None],
) -> None:
    assert path is not None  # None only in the skipped "no corpus" parameter
    original = path.read_bytes()
    record_property(SCHEMA_PROPERTY, schema)

    try:
        parsed = model.from_xml(original)
    except ValidationError as error:
        record_property(DIFFERENCES_PROPERTY, [_parse_error_summary(error)])
        raise

    found = list(differences(original, parsed.to_xml()))
    record_property(DIFFERENCES_PROPERTY, found)
    assert not found, "\n".join(found)


def _parse_error_summary(error: ValidationError) -> str:
    first = error.errors()[0]
    location = "/".join(str(part) for part in first["loc"])
    return f"parse error: {location}: {first['type']}"
