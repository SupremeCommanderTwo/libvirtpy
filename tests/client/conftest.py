"""Fixtures for the client tests: fake servers and test certificates."""

import shutil
import ssl
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.helpers.running_server import RunningServer


@pytest.fixture
def tcp_server() -> Iterator[RunningServer]:
    server = RunningServer(None)
    yield server
    server.close()


@pytest.fixture(scope="module")
def pki(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Make a CA and a server and client certificate with ``openssl``."""
    if shutil.which("openssl") is None:
        pytest.skip("openssl is not installed")
    directory = tmp_path_factory.mktemp("pki")

    def run(*arguments: str) -> None:
        subprocess.run(
            ["openssl", *arguments], cwd=directory, check=True, capture_output=True
        )

    run(
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        "ca.key",
        "-out",
        "cacert.pem",
        "-subj",
        "/CN=test-ca",
        "-days",
        "2",
    )
    for name in ("server", "client"):
        run(
            "req",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            f"{name}key.pem",
            "-out",
            f"{name}.csr",
            "-subj",
            "/CN=localhost",
        )
        (directory / f"{name}.ext").write_text(
            "subjectAltName=DNS:localhost,IP:127.0.0.1\n"
        )
        run(
            "x509",
            "-req",
            "-in",
            f"{name}.csr",
            "-CA",
            "cacert.pem",
            "-CAkey",
            "ca.key",
            "-CAcreateserial",
            "-out",
            f"{name}cert.pem",
            "-days",
            "2",
            "-extfile",
            f"{name}.ext",
        )
    return directory


@pytest.fixture
def tls_server(pki: Path) -> Iterator[RunningServer]:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(pki / "servercert.pem"), str(pki / "serverkey.pem"))
    context.load_verify_locations(cafile=str(pki / "cacert.pem"))
    context.verify_mode = ssl.CERT_REQUIRED
    server = RunningServer(context)
    yield server
    server.close()
