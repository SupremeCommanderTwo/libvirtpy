"""SASL mechanisms against the RFC test vectors, and the whole exchange."""

import asyncio
import base64
import ssl
from pathlib import Path

import pytest

from libvirtpy.client import LibvirtClient, SaslCredentials
from libvirtpy.rpc.errors import AuthFailedError
from libvirtpy.rpc.sasl import (
    DigestMd5,
    PlainMechanism,
    Scram,
    choose_mechanism,
    parse_mechanisms,
)
from tests.helpers.fake_rpc_server import HOSTNAME
from tests.helpers.running_server import RunningServer


def test_plain_sends_authzid_user_password() -> None:
    mechanism = PlainMechanism(SaslCredentials("joe", "pw"))

    assert mechanism.start() == b"\0joe\0pw"


def test_scram_sha1_matches_rfc_5802() -> None:
    scram = Scram(
        SaslCredentials("user", "pencil"), "sha1", nonce="fyko+d2lbbFgONRv9qkxdawL"
    )
    first = scram.start()

    final = scram.step(
        b"r=fyko+d2lbbFgONRv9qkxdawL3rfcNHYJY1ZVvWVs7j,s=QSXCR+Q6sek8bf92,i=4096"
    )
    scram.step(b"v=rmF9pqV8S7suAoZWja4dJRkFsKQ=")

    assert first == b"n,,n=user,r=fyko+d2lbbFgONRv9qkxdawL"
    assert final is not None
    assert final.endswith(b"p=v0X8v3Bz2T0CJGbJQyF0X+HI4Ts=")
    assert scram.finished


def test_scram_sha256_matches_rfc_7677() -> None:
    scram = Scram(
        SaslCredentials("user", "pencil"), "sha256", nonce="rOprNGfwEbeRWgbNEkqO"
    )
    scram.start()

    final = scram.step(
        b"r=rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0,"
        b"s=W22ZaJ0SNY7soEsUEjb6gQ==,i=4096"
    )
    scram.step(b"v=6rriTRBi23WpRR/wtup+mMhUZUn/dB5nLTJRsjl95G4=")

    assert final is not None
    assert final.endswith(b"p=dHzbZapWIk4jUhN+Ute9ytag9zjfMHgsqmmiz7AndVQ=")


def test_scram_rejects_a_server_that_does_not_know_the_password() -> None:
    scram = Scram(SaslCredentials("user", "pencil"), "sha256", nonce="abc")
    scram.start()
    scram.step(b"r=abcdef,s=" + base64.b64encode(b"salt") + b",i=4096")

    with pytest.raises(AuthFailedError, match="prove"):
        scram.step(b"v=" + base64.b64encode(b"wrong"))


def test_scram_rejects_a_server_nonce_that_does_not_extend_ours() -> None:
    scram = Scram(SaslCredentials("user", "pw"), "sha1", nonce="mine")
    scram.start()

    with pytest.raises(AuthFailedError):
        scram.step(b"r=other,s=c2FsdA==,i=1")


def test_digest_md5_matches_rfc_2831() -> None:
    mechanism = DigestMd5(
        SaslCredentials("chris", "secret"),
        "elwood.innosoft.com",
        cnonce="OA6MHXh6VqTrRk",
        service="imap",
    )

    response = mechanism.step(
        b'realm="elwood.innosoft.com",nonce="OA6MG9tEQGm2hh",qop="auth",'
        b"algorithm=md5-sess,charset=utf-8"
    )
    final = mechanism.step(b"rspauth=ea40f60335c427b5527b84dbabcdfffd")

    assert response is not None
    assert b"response=d388dad90d4bbd760a152321f2143af7" in response
    assert b'digest-uri="imap/elwood.innosoft.com"' in response
    assert final == b""
    assert mechanism.finished


def test_digest_md5_refuses_a_security_layer_only_server() -> None:
    mechanism = DigestMd5(SaslCredentials("u", "p"), "h")

    with pytest.raises(AuthFailedError, match="security layer"):
        mechanism.step(b'nonce="n",qop="auth-conf"')


def test_the_best_common_mechanism_is_chosen() -> None:
    credentials = SaslCredentials("u", "p")

    best = choose_mechanism(
        ["PLAIN", "DIGEST-MD5", "SCRAM-SHA-256", "GSSAPI"], credentials, "h"
    )
    fallback = choose_mechanism(["GSSAPI", "PLAIN"], credentials, "h")

    assert best.name == "SCRAM-SHA-256"
    assert fallback.name == "PLAIN"


def test_no_common_mechanism_is_an_auth_error() -> None:
    with pytest.raises(AuthFailedError, match="no common"):
        choose_mechanism(["GSSAPI"], SaslCredentials("u", "p"), "h")


@pytest.fixture
def sasl_tls_server(pki: Path, request: pytest.FixtureRequest) -> RunningServer:
    mechanism = getattr(request, "param", "SCRAM-SHA-256")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(pki / "servercert.pem"), str(pki / "serverkey.pem"))
    context.load_verify_locations(cafile=str(pki / "cacert.pem"))
    context.verify_mode = ssl.CERT_REQUIRED
    return RunningServer(context, sasl=(mechanism, "alice", "wonderland"))


@pytest.mark.parametrize(
    "sasl_tls_server", ["SCRAM-SHA-256", "SCRAM-SHA-1", "PLAIN"], indirect=True
)
def test_client_authenticates_over_tls(
    sasl_tls_server: RunningServer, pki: Path
) -> None:
    uri = f"qemu+tls://localhost:{sasl_tls_server.port}/system?pkipath={pki}"

    with LibvirtClient.open(uri, sasl=SaslCredentials("alice", "wonderland")) as client:
        hostname = client.get_hostname()

    assert hostname == HOSTNAME


def test_wrong_password_is_an_auth_failure(
    sasl_tls_server: RunningServer, pki: Path
) -> None:
    uri = f"qemu+tls://localhost:{sasl_tls_server.port}/system?pkipath={pki}"

    with pytest.raises(AuthFailedError):
        LibvirtClient.open(uri, sasl=SaslCredentials("alice", "nope"))


def test_missing_credentials_are_explained(
    sasl_tls_server: RunningServer, pki: Path
) -> None:
    uri = f"qemu+tls://localhost:{sasl_tls_server.port}/system?pkipath={pki}"

    with pytest.raises(AuthFailedError, match="sasl=SaslCredentials"):
        LibvirtClient.open(uri)


def test_sasl_over_plain_tcp_is_refused_before_sending_a_password() -> None:
    server = RunningServer(None, sasl=("PLAIN", "alice", "wonderland"))
    try:
        uri = f"qemu+tcp://127.0.0.1:{server.port}/system"

        with pytest.raises(AuthFailedError, match="security layer"):
            LibvirtClient.open(uri, sasl=SaslCredentials("alice", "wonderland"))
    finally:
        server.close()


def test_async_client_authenticates_over_tls(
    sasl_tls_server: RunningServer, pki: Path
) -> None:
    from libvirtpy.client import AsyncLibvirtClient

    async def scenario() -> str:
        uri = f"qemu+tls://localhost:{sasl_tls_server.port}/system?pkipath={pki}"
        credentials = SaslCredentials("alice", "wonderland")
        async with await AsyncLibvirtClient.open(uri, sasl=credentials) as client:
            return await client.get_hostname()

    assert asyncio.run(scenario()) == HOSTNAME


@pytest.mark.parametrize(
    "offered",
    [
        "SCRAM-SHA-256,DIGEST-MD5,PLAIN",
        "SCRAM-SHA-256 DIGEST-MD5 PLAIN",
        " SCRAM-SHA-256, DIGEST-MD5 ,PLAIN,",
    ],
)
def test_the_daemons_mechanism_list_is_split_on_commas_and_spaces(offered: str) -> None:
    """A real daemon sends one comma-separated string, not a space-separated one."""
    assert parse_mechanisms(offered) == ["SCRAM-SHA-256", "DIGEST-MD5", "PLAIN"]
