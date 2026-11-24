"""The sans-I/O RPC session: framing, replies, errors, keepalive."""

import pytest

from libvirtpy.rpc import xdr
from libvirtpy.rpc.errors import NoDomainError
from libvirtpy.rpc.protocol import procedures, types
from libvirtpy.rpc.session import ProtocolError, Session

HEADER = xdr.StructType(types.VirNetMessageHeader)


def reply_packet(
    serial: int, procedure_number: int, payload: bytes, *, error: bool = False
) -> bytes:
    """Frame a reply the way a daemon would."""
    header = types.VirNetMessageHeader(
        prog=types.REMOTE_PROGRAM,
        vers=types.REMOTE_PROTOCOL_VERSION,
        proc=procedure_number,
        type=types.VirNetMessageType.REPLY,
        serial=serial,
        status=types.VirNetMessageStatus.ERROR
        if error
        else types.VirNetMessageStatus.OK,
    )
    body = xdr.encode(HEADER, header) + payload
    return (4 + len(body)).to_bytes(4, "big") + body


def version_payload(number: int) -> bytes:
    """Encode a ``connect_get_lib_version`` reply."""
    return xdr.encode(
        xdr.StructType(types.ConnectGetLibVersionRet),
        types.ConnectGetLibVersionRet(lib_ver=number),
    )


def test_call_frames_a_header_and_the_encoded_arguments() -> None:
    session = Session()

    serial, packet = session.call(
        procedures.DOMAIN_LOOKUP_BY_NAME, types.DomainLookupByNameArgs(name="vm")
    )

    assert serial == 1
    assert int.from_bytes(packet[:4], "big") == len(packet)
    assert packet[4:8].hex() == "20008086"
    assert packet[-8:] == b"\x00\x00\x00\x02vm\x00\x00"


def test_reply_completes_the_call_with_the_decoded_result() -> None:
    session = Session()
    serial, _ = session.call(procedures.CONNECT_GET_LIB_VERSION)

    (done,) = session.feed(
        reply_packet(
            serial, procedures.CONNECT_GET_LIB_VERSION.number, version_payload(11006000)
        )
    )

    assert done.serial == serial
    assert done.result.lib_ver == 11006000


def test_a_reply_split_in_pieces_is_assembled() -> None:
    session = Session()
    serial, _ = session.call(procedures.CONNECT_GET_LIB_VERSION)
    packet = reply_packet(
        serial, procedures.CONNECT_GET_LIB_VERSION.number, version_payload(5)
    )

    first = session.feed(packet[:10])
    second = session.feed(packet[10:])

    assert first == []
    assert [item.result.lib_ver for item in second] == [5]


def test_error_reply_becomes_the_matching_exception() -> None:
    session = Session()
    serial, _ = session.call(procedures.CONNECT_GET_LIB_VERSION)
    error = types.Error(
        code=42,
        domain=10,
        message="no such domain",
        level=2,
        dom=None,
        str1=None,
        str2=None,
        str3=None,
        int1=0,
        int2=0,
        net=None,
    )
    payload = xdr.encode(xdr.StructType(types.Error), error)

    (done,) = session.feed(reply_packet(serial, 1, payload, error=True))

    assert isinstance(done.error, NoDomainError)
    assert done.error.message == "no such domain"


def test_keepalive_ping_is_answered_with_a_pong() -> None:
    session = Session()
    ping = types.VirNetMessageHeader(
        prog=types.KEEPALIVE_PROGRAM,
        vers=types.KEEPALIVE_PROTOCOL_VERSION,
        proc=int(types.KeepaliveProcedure.PING),
        type=types.VirNetMessageType.MESSAGE,
        serial=9,
        status=types.VirNetMessageStatus.OK,
    )
    body = xdr.encode(HEADER, ping)

    done = session.feed((4 + len(body)).to_bytes(4, "big") + body)
    pong = session.take_outgoing()

    assert done == []
    assert pong[4 + 8 : 4 + 12] == int(types.KeepaliveProcedure.PONG).to_bytes(4, "big")
    assert session.take_outgoing() == b""


@pytest.mark.parametrize("length", [3, 27, 2**31])
def test_impossible_packet_length_is_a_protocol_error(length: int) -> None:
    with pytest.raises(ProtocolError):
        Session().feed(length.to_bytes(4, "big") + bytes(40))


def test_reply_to_an_unknown_serial_is_a_protocol_error() -> None:
    with pytest.raises(ProtocolError):
        Session().feed(reply_packet(77, 1, b""))


def test_wrong_arguments_are_rejected_before_sending() -> None:
    with pytest.raises(ProtocolError):
        Session().call(
            procedures.CONNECT_GET_LIB_VERSION, types.DomainLookupByNameArgs(name="x")
        )
