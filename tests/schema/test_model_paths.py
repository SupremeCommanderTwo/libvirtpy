import pytest

from tests.helpers.corpus import MISSING_CORPUS_MESSAGE, corpus_version
from tools.schema_coverage import ROOT_MODELS, coverage

pytestmark = pytest.mark.corpus


@pytest.mark.parametrize("root", sorted(ROOT_MODELS))
def test_every_modelled_path_exists_in_the_schema(root: str) -> None:
    if corpus_version() is None:
        pytest.skip(MISSING_CORPUS_MESSAGE)

    unknown = sorted(coverage(root).unknown)

    assert not unknown, "\n".join(unknown)
