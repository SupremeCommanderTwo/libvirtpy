"""Examples with a real connection: they explain themselves and fail politely."""

import runpy
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REAL = Path(__file__).resolve().parents[2] / "examples" / "real"
SCRIPTS = sorted(REAL.glob("[0-9]*.py"))


@dataclass(frozen=True)
class Outcome:
    """What an example did: its exit status and what it printed."""

    returncode: int
    stdout: str
    stderr: str


def run(
    script: Path,
    *arguments: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    path: str | None = None,
) -> Outcome:
    """Run an example inside this process, as ``python script.py arguments`` would.

    Starting a Python process for each example costs the import of the library
    (0.8 s each), so only ``test_example_runs_as_a_script`` does that.
    """
    monkeypatch.syspath_prepend(str(REAL))
    monkeypatch.setattr(sys, "argv", [str(script), *arguments])
    if path is not None:
        monkeypatch.setenv("PATH", path)

    # examples/common.py (the fake-daemon examples) has the same module name
    other_common = sys.modules.pop("common", None)
    returncode = 0
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as stop:
        returncode = stop.code if isinstance(stop.code, int) else 1
    finally:
        sys.modules.pop("common", None)
        if other_common is not None:
            sys.modules["common"] = other_common

    captured = capsys.readouterr()
    return Outcome(returncode, captured.out, captured.err)


def test_example_runs_as_a_script() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS[0]), "--help"],
        cwd=REAL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.stem)
def test_example_explains_itself(
    script: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = run(script, "--help", capsys=capsys, monkeypatch=monkeypatch)

    assert result.returncode == 0
    assert "usage:" in result.stdout


@pytest.mark.parametrize(
    "script",
    [
        s
        for s in SCRIPTS
        if s.stem not in ("06_async_many_hosts", "10_screenshot_and_download")
    ],
    ids=lambda path: path.stem,
)
def test_unreachable_host_is_a_message_not_a_traceback(
    script: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = run(
        script,
        "qemu+tcp://127.0.0.1:1/system",
        capsys=capsys,
        monkeypatch=monkeypatch,
        path="/usr/bin:/bin",
    )

    if script.stem == "05_tls_with_sasl":
        assert result.returncode == 2
        return
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith("error:")


def test_async_example_reports_each_failing_host(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = run(
        REAL / "06_async_many_hosts.py",
        "qemu+tcp://127.0.0.1:1/system",
        capsys=capsys,
        monkeypatch=monkeypatch,
    )

    assert result.returncode == 0
    assert "FAILED" in result.stdout


@pytest.mark.libvirt
def test_local_example_lists_the_real_host(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = run(REAL / "01_local_system.py", capsys=capsys, monkeypatch=monkeypatch)

    if "no libvirt socket" in result.stderr:
        pytest.skip("no libvirt daemon on this machine")
    assert result.returncode == 0
    assert "hypervisor version" in result.stdout
