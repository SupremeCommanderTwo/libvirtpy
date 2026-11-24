"""The generated protocol matches what ``tools/gen_protocol.py`` produces."""

import pytest

from tools.gen_protocol import SOURCES, generate


@pytest.mark.corpus
def test_generated_protocol_is_up_to_date() -> None:
    if not SOURCES[0].exists():
        pytest.skip("libvirt corpus not fetched: run tools/fetch_samples.py")

    stale = [
        path.name
        for path, text in generate().items()
        if path.read_text(encoding="utf-8") != text
    ]

    assert not stale, f"run tools/gen_protocol.py: {stale}"
