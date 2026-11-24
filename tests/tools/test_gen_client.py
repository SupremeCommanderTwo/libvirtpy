"""The generated clients match what ``tools/gen_client.py`` produces."""

from tools.gen_client import generate


def test_generated_clients_are_up_to_date() -> None:
    stale = [
        path.name
        for path, text in generate().items()
        if path.read_text(encoding="utf-8") != text
    ]

    assert not stale, f"run tools/gen_client.py: {stale}"
