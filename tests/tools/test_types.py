"""The whole project passes ``mypy --strict`` (configured in ``pyproject.toml``)."""

from pathlib import Path

from mypy import api

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_the_project_passes_mypy_strict() -> None:
    config = str(REPOSITORY_ROOT / "pyproject.toml")

    stdout, stderr, status = api.run(["--config-file", config])

    assert status == 0, stdout + stderr
