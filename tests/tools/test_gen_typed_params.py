"""The typed-parameter hints match what ``tools/gen_typed_params.py`` produces."""

import pytest

from tools.gen_typed_params import HEADERS, OUTPUT, generate


@pytest.mark.corpus
def test_typed_hints_are_up_to_date() -> None:
    if not HEADERS.exists():
        pytest.skip("libvirt corpus not fetched: run tools/fetch_samples.py")

    assert OUTPUT.read_text(encoding="utf-8") == generate()
