"""Finding daemons and choosing how to authenticate, without any I/O."""

from pathlib import Path

import pytest

from libvirtpy.rpc.errors import AuthFailedError
from libvirtpy.rpc.protocol import procedures, types
from libvirtpy.rpc.sockets import (
    CONNECT_READ_ONLY,
    _connect_first,
    authentication,
    open_arguments,
    socket_paths,
)
from libvirtpy.rpc.uri import parse_uri


def test_no_authentication_needs_no_calls() -> None:
    steps = authentication([types.AuthType.NONE], parse_uri("qemu:///system"), None)

    assert list(steps) == []


def test_polkit_is_one_call() -> None:
    steps = authentication([types.AuthType.POLKIT], parse_uri("qemu:///system"), None)

    assert list(steps) == [(procedures.AUTH_POLKIT, None)]


def test_an_empty_offer_is_an_auth_error() -> None:
    steps = authentication([], parse_uri("qemu:///system"), None)

    with pytest.raises(AuthFailedError, match="not supported"):
        next(steps)


def test_a_missing_socket_is_a_connection_error_naming_the_path(tmp_path: Path) -> None:
    missing = tmp_path / "libvirt-sock"

    with pytest.raises(ConnectionError, match="libvirt-sock"):
        _connect_first([missing], None)


def test_the_primary_daemon_is_opened_with_the_users_uri() -> None:
    target = parse_uri("qemu:///system")
    path = Path("/run/libvirt/virtqemud-sock")

    arguments = open_arguments(target, "hypervisor", path, read_only=True)

    assert arguments.name == "qemu:///system"
    assert arguments.flags == CONNECT_READ_ONLY


def test_a_secondary_daemon_is_opened_with_its_own_scheme() -> None:
    path = Path("/run/libvirt/virtnetworkd-sock")

    system = open_arguments(parse_uri("qemu:///system"), "network", path, False)
    session = open_arguments(parse_uri("qemu:///session"), "network", path, False)

    assert system.name == "network:///system"
    assert session.name == "network:///session"
    assert system.flags == 0


def test_the_monolithic_daemon_serves_every_driver_with_the_users_uri() -> None:
    path = Path("/run/libvirt/libvirt-sock")

    arguments = open_arguments(parse_uri("qemu:///system"), "storage", path, False)

    assert arguments.name == "qemu:///system"


def test_modular_sockets_come_before_the_monolithic_one() -> None:
    paths = socket_paths(parse_uri("qemu:///system"), "network", read_only=False)

    assert paths[0].name == "virtnetworkd-sock"
    assert paths[1].name == "libvirt-sock"
    assert [
        path.name
        for path in socket_paths(
            parse_uri("qemu:///system"), "hypervisor", read_only=True
        )
    ] == ["virtqemud-sock-ro", "libvirt-sock-ro"]
