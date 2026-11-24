"""Remote transports against a fake daemon: ssh, tls and tcp, sync and async."""

import asyncio
import shlex
import ssl
import subprocess
import sys
from pathlib import Path

import pytest

from libvirtpy.client import AsyncLibvirtClient, LibvirtClient
from libvirtpy.rpc.remote import ssh_command, tls_files
from libvirtpy.rpc.uri import parse_uri
from tests.helpers.fake_rpc_server import HOSTNAME
from tests.helpers.running_server import RunningServer

SERVER_SCRIPT = Path(__file__).resolve().parents[1] / "helpers" / "fake_rpc_server.py"


def test_ssh_command_prefers_the_helper_and_falls_back_to_netcat() -> None:
    target = parse_uri("qemu+ssh://root@host:2222/system?keyfile=/k")

    command = ssh_command(target)

    assert command[:3] == ["ssh", "-T", "-e"]
    assert command[command.index("-p") + 1] == "2222"
    assert command[command.index("-i") + 1] == "/k"
    assert "root@host" in command
    script = shlex.split(command[-1])[2]
    assert "virt-ssh-helper qemu:///system" in script
    assert "nc -U /var/run/libvirt/libvirt-sock" in script


def test_ssh_proxy_can_be_forced() -> None:
    native = shlex.split(
        ssh_command(parse_uri("qemu+ssh://h/system?proxy=native"))[-1]
    )[2]
    netcat = shlex.split(
        ssh_command(
            parse_uri("qemu+ssh://h/session?proxy=netcat&socket=/s&netcat=ncat")
        )[-1]
    )[2]

    assert native == "exec virt-ssh-helper qemu:///system"
    assert netcat == "exec ncat -U /s"


def test_remote_shell_runs_the_whole_script(tmp_path: Path) -> None:
    """A real sshd joins the arguments and lets the login shell parse them again.

    The first version sent ``sh -c if ...; then ...`` unquoted, which the remote
    shell rejected with a syntax error.
    """
    fake_helper = tmp_path / "virt-ssh-helper"
    fake_helper.write_text('#!/bin/sh\necho helper-ran "$@"\n')
    fake_helper.chmod(0o755)
    command = ssh_command(parse_uri("qemu+ssh://me@h/system"))
    arguments = command[1:]
    destination = arguments.index("me@h")
    remote = " ".join(arguments[destination + 1 :])

    result = subprocess.run(
        ["sh", "-c", remote],
        env={"PATH": f"{tmp_path}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.stderr == ""
    assert result.stdout == "helper-ran qemu:///system\n"


def test_unknown_ssh_proxy_is_rejected() -> None:
    with pytest.raises(ValueError, match="proxy"):
        ssh_command(parse_uri("qemu+ssh://h/system?proxy=magic"))


def test_pkipath_names_the_certificate_files() -> None:
    files = tls_files(parse_uri("qemu+tls://h/system?pkipath=/pki"))

    assert (files.ca, files.certificate, files.key) == (
        Path("/pki/cacert.pem"),
        Path("/pki/clientcert.pem"),
        Path("/pki/clientkey.pem"),
    )


def test_remote_uri_defaults_and_open_name() -> None:
    tls = parse_uri("qemu+tls://user@host/system")
    tcp = parse_uri("lxc+tcp://host/session?x=1")

    assert (tls.port, tls.user, tls.host) == (16514, "user", "host")
    assert (tcp.port, tcp.open_name) == (16509, "lxc:///session")


def test_tcp_client_opens_the_stripped_uri_and_calls(tcp_server: RunningServer) -> None:
    uri = f"qemu+tcp://127.0.0.1:{tcp_server.port}/system?ignored=1"

    with LibvirtClient.open(uri, read_only=True) as client:
        hostname = client.get_hostname()

    assert hostname == HOSTNAME
    assert tcp_server.daemon.opened == ["qemu:///system"]
    assert tcp_server.daemon.flags == [1]


def test_tls_client_presents_its_certificate(
    tls_server: RunningServer, pki: Path
) -> None:
    uri = f"qemu+tls://localhost:{tls_server.port}/system?pkipath={pki}"

    with LibvirtClient.open(uri) as client:
        hostname = client.get_hostname()

    assert hostname == HOSTNAME


def test_tls_server_certificate_is_verified(
    tls_server: RunningServer, tmp_path: Path
) -> None:
    other = tmp_path / "cacert.pem"
    other.write_text("")
    uri = f"qemu+tls://localhost:{tls_server.port}/system?pkipath={tmp_path}"

    with pytest.raises((ConnectionError, ssl.SSLError, ValueError)):
        LibvirtClient.open(uri)


def test_tls_without_a_client_certificate_is_refused(
    tls_server: RunningServer, pki: Path, tmp_path: Path
) -> None:
    (tmp_path / "cacert.pem").write_bytes((pki / "cacert.pem").read_bytes())
    uri = f"qemu+tls://localhost:{tls_server.port}/system?pkipath={tmp_path}"

    with pytest.raises(
        Exception, match=r"(?i)certificate|handshake|closed|reset|ssl|tls"
    ):
        LibvirtClient.open(uri)


def test_ssh_client_runs_the_ssh_program_and_talks_through_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arguments_file = tmp_path / "arguments"
    script = tmp_path / "fake-ssh"
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > {arguments_file}\n'
        f"exec {sys.executable} {SERVER_SCRIPT}\n"
    )
    script.chmod(0o755)
    monkeypatch.setenv("PYTHONPATH", str(Path(SERVER_SCRIPT).parents[2]))
    uri = f"qemu+ssh://me@example.org/system?command={script}&proxy=native"

    with LibvirtClient.open(uri) as client:
        hostname = client.get_hostname()

    assert hostname == HOSTNAME
    recorded = arguments_file.read_text().splitlines()
    assert "me@example.org" in recorded
    assert shlex.split(recorded[-1])[2] == "exec virt-ssh-helper qemu:///system"


def test_missing_ssh_program_is_a_connection_error() -> None:
    with pytest.raises(ConnectionError, match="ssh"):
        LibvirtClient.open("qemu+ssh://h/system?command=/nonexistent/ssh")


def test_async_client_over_tcp(tcp_server: RunningServer) -> None:
    async def scenario() -> list[str]:
        client = await AsyncLibvirtClient.open(
            f"qemu+tcp://127.0.0.1:{tcp_server.port}/system"
        )
        async with client:
            return list(
                await asyncio.gather(client.get_hostname(), client.get_hostname())
            )

    assert asyncio.run(scenario()) == [HOSTNAME, HOSTNAME]


def test_async_client_over_tls(tls_server: RunningServer, pki: Path) -> None:
    async def scenario() -> str:
        uri = f"qemu+tls://localhost:{tls_server.port}/system?pkipath={pki}"
        async with await AsyncLibvirtClient.open(uri) as client:
            return await client.get_hostname()

    assert asyncio.run(scenario()) == HOSTNAME


def test_async_client_over_ssh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "fake-ssh"
    script.write_text(f"#!/bin/sh\nexec {sys.executable} {SERVER_SCRIPT}\n")
    script.chmod(0o755)
    monkeypatch.setenv("PYTHONPATH", str(Path(SERVER_SCRIPT).parents[2]))

    async def scenario() -> str:
        async with await AsyncLibvirtClient.open(
            f"qemu+ssh://h/system?command={script}"
        ) as client:
            return await client.get_hostname()

    assert asyncio.run(scenario()) == HOSTNAME


def test_ssh_that_exits_is_a_connection_error(tmp_path: Path) -> None:
    script = tmp_path / "failing-ssh"
    script.write_text("#!/bin/sh\nexit 255\n")
    script.chmod(0o755)

    with pytest.raises(ConnectionError):
        LibvirtClient.open(f"qemu+ssh://h/system?command={script}")


def test_async_ssh_that_exits_is_a_connection_error(tmp_path: Path) -> None:
    script = tmp_path / "failing-ssh"
    script.write_text("#!/bin/sh\nexit 255\n")
    script.chmod(0o755)

    async def scenario() -> None:
        await AsyncLibvirtClient.open(f"qemu+ssh://h/system?command={script}")

    with pytest.raises(ConnectionError):
        asyncio.run(scenario())


def test_pkipath_expands_the_home_directory_and_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", "/home/me")

    from_variable = tls_files(parse_uri("qemu+tls://h/system?pkipath=$HOME/pki"))
    from_tilde = tls_files(parse_uri("qemu+tls://h/system?pkipath=~/pki"))

    assert from_variable.ca == Path("/home/me/pki/cacert.pem")
    assert from_tilde.ca == Path("/home/me/pki/cacert.pem")


def test_a_pkipath_without_a_ca_is_an_error_not_the_system_store(
    tls_server: RunningServer, tmp_path: Path
) -> None:
    uri = f"qemu+tls://localhost:{tls_server.port}/system?pkipath={tmp_path}/missing"

    with pytest.raises(ConnectionError, match="no CA certificate"):
        LibvirtClient.open(uri)
