"""The examples run to the end against the fake daemon, so they cannot rot."""

import runpy
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


@pytest.mark.parametrize(
    "script", sorted(EXAMPLES.glob("0*.py")), ids=lambda path: path.stem
)
def test_example_runs(script: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(EXAMPLES))
    monkeypatch.delitem(sys.modules, "common", raising=False)

    runpy.run_path(str(script), run_name="__main__")
