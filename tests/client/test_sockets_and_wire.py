"""URI and socket choice, and the conversion between operations and the wire."""

from pathlib import Path

import pytest

from libvirtpy.client import wire
from libvirtpy.client.transport import Handle
from libvirtpy.rpc.protocol import procedures, types
from libvirtpy.rpc.session import ProtocolError
from libvirtpy.rpc.sockets import parse_uri, socket_paths

UUID_TEXT = "01234567-89ab-cdef-0123-456789abcdef"


def test_system_uri_prefers_the_modular_daemon_then_libvirtd() -> None:
    target = parse_uri("qemu:///system")

    paths = socket_paths(target, "hypervisor", read_only=False)

    assert paths == [
        Path("/run/libvirt/virtqemud-sock"),
        Path("/run/libvirt/libvirt-sock"),
    ]


def test_secondary_drivers_have_their_own_daemon() -> None:
    target = parse_uri("qemu:///system")

    paths = socket_paths(target, "network", read_only=True)

    assert paths[0] == Path("/run/libvirt/virtnetworkd-sock-ro")


def test_session_uri_uses_the_runtime_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")

    paths = socket_paths(parse_uri("qemu:///session"), "hypervisor", read_only=False)

    assert paths[0] == Path("/run/user/1000/libvirt/virtqemud-sock")


def test_unknown_driver_is_a_value_error() -> None:
    with pytest.raises(ValueError, match="unknown"):
        parse_uri("nothing:///system")


def test_arguments_with_a_wrong_name_are_rejected() -> None:
    with pytest.raises(ProtocolError):
        wire.convert_arguments(procedures.DOMAIN_LOOKUP_BY_NAME, {"nom": "vm"})


def test_uuid_text_becomes_sixteen_bytes() -> None:
    args = wire.convert_arguments(procedures.DOMAIN_LOOKUP_BY_UUID, {"uuid": UUID_TEXT})

    assert args.uuid == bytes.fromhex(UUID_TEXT.replace("-", ""))


def test_handle_returned_by_a_daemon_is_sent_back_as_its_struct() -> None:
    struct = types.NonnullDomain(name="vm", uuid=bytes(16), id=3)
    handle = wire._from_wire(struct)

    args = wire.convert_arguments(
        procedures.DOMAIN_GET_XML_DESC, {"dom": handle, "flags": 0}
    )

    assert isinstance(handle, Handle)
    assert (handle.name, handle.id) == ("vm", 3)
    assert args.dom is struct


def test_a_handle_that_did_not_come_from_a_daemon_is_refused() -> None:
    with pytest.raises(ProtocolError):
        wire.convert_arguments(
            procedures.DOMAIN_GET_XML_DESC, {"dom": Handle(name="vm"), "flags": 0}
        )


def test_inactive_domain_has_no_runtime_id() -> None:
    handle = wire._from_wire(types.NonnullDomain(name="vm", uuid=bytes(16), id=-1))

    assert handle.id is None


def test_list_reply_is_unwrapped_to_handles() -> None:
    reply = types.ConnectListAllDomainsRet(
        domains=[types.NonnullDomain(name="a", uuid=bytes(16), id=-1)], ret=1
    )

    handles = wire.convert_reply(procedures.CONNECT_LIST_ALL_DOMAINS, reply)

    assert [handle.name for handle in handles] == ["a"]


def test_text_argument_may_be_given_a_handle_for_node_devices() -> None:
    handle = wire._from_wire(types.NonnullNodeDevice(name="pci_0000_00_1f_2"))

    args = wire.convert_arguments(
        procedures.NODE_DEVICE_GET_XML_DESC, {"name": handle, "flags": 0}
    )

    assert args.name == "pci_0000_00_1f_2"


@pytest.mark.parametrize(
    "uri", ["qemu+ssh:///system", "qemu://h/system", "qemu+tls:///"]
)
def test_inconsistent_hosts_are_value_errors(uri: str) -> None:
    with pytest.raises(ValueError, match="host"):
        parse_uri(uri)


def test_unknown_transport_is_not_supported() -> None:
    with pytest.raises(NotImplementedError):
        parse_uri("qemu+libssh2://h/system")
