"""Hostile input: a daemon (or whoever answers on the socket) must not crash the client.

The inputs are random but seeded, so a failure is reproducible. Whatever bytes
arrive, the library may only raise its own errors (``LibvirtPyError``), never an
``IndexError``, ``struct.error``, ``MemoryError`` or the like, and must not hang.
"""

import contextlib
import random
import time

import pytest

from libvirtpy.errors import LibvirtPyError
from libvirtpy.rpc import xdr
from libvirtpy.rpc.procedure import Procedure
from libvirtpy.rpc.protocol import procedures, types
from libvirtpy.rpc.sasl import (
    DigestMd5,
    SaslCredentials,
    Scram,
    parse_mechanisms,
)
from libvirtpy.rpc.session import Session
from libvirtpy.rpc.uri import parse_uri

ROUNDS = 400
SEEDS = [1, 2, 3]
TIME_LIMIT_SECONDS = 20


def random_bytes(generator: random.Random, limit: int = 300) -> bytes:
    return generator.randbytes(generator.randrange(0, limit))


def mutate(generator: random.Random, data: bytes) -> bytes:
    """Flip, drop, insert or repeat bytes of a valid packet."""
    buffer = bytearray(data)
    for _ in range(generator.randrange(1, 6)):
        if not buffer:
            break
        position = generator.randrange(len(buffer))
        action = generator.choice(["flip", "drop", "insert", "truncate", "repeat"])
        if action == "flip":
            buffer[position] = generator.randrange(256)
        elif action == "drop":
            del buffer[position]
        elif action == "insert":
            buffer.insert(position, generator.randrange(256))
        elif action == "truncate":
            del buffer[position:]
        else:
            buffer[position:position] = buffer[position : position + 8]
    return bytes(buffer)


def reply_packet(serial: int, payload: bytes, *, error: bool = False) -> bytes:
    header = types.VirNetMessageHeader(
        prog=types.REMOTE_PROGRAM,
        vers=types.REMOTE_PROTOCOL_VERSION,
        proc=1,
        type=types.VirNetMessageType.REPLY,
        serial=serial,
        status=types.VirNetMessageStatus.ERROR
        if error
        else types.VirNetMessageStatus.OK,
    )
    body = xdr.encode(xdr.StructType(types.VirNetMessageHeader), header) + payload
    return (4 + len(body)).to_bytes(4, "big") + body


def struct_types() -> list[xdr.StructType]:
    return [
        xdr.StructType(struct)
        for procedure in procedures.PROCEDURES.values()
        for struct in (procedure.args, procedure.ret, procedure.message)
        if struct is not None
    ]


@pytest.mark.parametrize("seed", SEEDS)
def test_decoding_random_bytes_only_raises_our_errors(seed: int) -> None:
    generator = random.Random(seed)
    candidates = struct_types()
    started = time.monotonic()

    for _ in range(ROUNDS):
        data = random_bytes(generator)
        for candidate in generator.sample(candidates, 25):
            with contextlib.suppress(LibvirtPyError):
                xdr.decode(candidate, data)

    assert time.monotonic() - started < TIME_LIMIT_SECONDS


@pytest.mark.parametrize("seed", SEEDS)
def test_mutated_valid_values_only_raise_our_errors(seed: int) -> None:
    generator = random.Random(seed)
    error = types.Error(
        code=42, domain=10, message="boom", level=2, dom=None, str1=None,
        str2=None, str3=None, int1=1, int2=2, net=None,
    )  # fmt: skip
    valid = xdr.encode(xdr.StructType(types.Error), error)

    for _ in range(ROUNDS * 4):
        with contextlib.suppress(LibvirtPyError):
            xdr.decode(xdr.StructType(types.Error), mutate(generator, valid))


@pytest.mark.parametrize("seed", SEEDS)
def test_session_survives_garbage_after_a_call(seed: int) -> None:
    generator = random.Random(seed)
    procedure: Procedure[object, object] = procedures.CONNECT_GET_VERSION

    for _ in range(ROUNDS):
        session = Session()
        serial, _ = session.call(procedure)
        packet = reply_packet(serial, b"\x00\x00\x00\x01\x00\x00\x00\x02")
        data = (
            mutate(generator, packet)
            if generator.random() < 0.7
            else random_bytes(generator)
        )
        with contextlib.suppress(LibvirtPyError):
            session.feed(data)


def test_every_prefix_of_a_reply_is_either_incomplete_or_valid() -> None:
    session = Session()
    serial, _ = session.call(procedures.CONNECT_GET_VERSION)
    packet = reply_packet(serial, b"\x00\x00\x00\x00\x00\x00\x00\x07")

    for cut in range(len(packet)):
        probe = Session()
        probe.call(procedures.CONNECT_GET_VERSION)
        assert probe.feed(packet[:cut]) == []

    assert len(session.feed(packet)) == 1


def test_an_absurd_length_is_refused_before_it_is_buffered() -> None:
    session = Session()
    session.call(procedures.CONNECT_GET_VERSION)

    with pytest.raises(LibvirtPyError):
        session.feed((0xFFFFFFF0).to_bytes(4, "big"))


def test_a_reply_nobody_asked_for_is_an_error() -> None:
    session = Session()

    with pytest.raises(LibvirtPyError):
        session.feed(reply_packet(99, b""))


@pytest.mark.parametrize("seed", SEEDS)
def test_sasl_mechanisms_survive_hostile_challenges(seed: int) -> None:
    generator = random.Random(seed)
    credentials = SaslCredentials("user", "password")

    for _ in range(ROUNDS):
        for mechanism in (
            Scram(credentials, "sha256"),
            DigestMd5(credentials, "h"),
        ):
            mechanism.start()
            try:
                mechanism.step(random_bytes(generator, 200))
                mechanism.step(random_bytes(generator, 200))
            except LibvirtPyError:
                pass


@pytest.mark.parametrize("seed", SEEDS)
def test_mechanism_lists_and_uris_never_crash(seed: int) -> None:
    generator = random.Random(seed)
    alphabet = "abc:/@?&=%[]. ,-\x00é"

    for _ in range(ROUNDS * 2):
        text = "".join(
            generator.choice(alphabet) for _ in range(generator.randrange(40))
        )
        parse_mechanisms(text)
        with contextlib.suppress(ValueError, NotImplementedError):
            parse_uri(text)


def test_a_huge_scram_iteration_count_is_refused_not_computed() -> None:
    mechanism = Scram(SaslCredentials("u", "p"), "sha256", nonce="abc")
    mechanism.start()
    started = time.monotonic()

    with pytest.raises(LibvirtPyError, match="iteration"):
        mechanism.step(b"r=abcdef,s=c2FsdA==,i=2000000000")

    assert time.monotonic() - started < 1


@pytest.mark.parametrize("seed", SEEDS)
def test_mutated_replies_of_every_procedure_only_raise_our_errors(seed: int) -> None:
    from tests.helpers.synthetic_daemon import sample

    generator = random.Random(seed)

    for procedure in procedures.PROCEDURES.values():
        if procedure.ret is None:
            continue
        reply_type = xdr.StructType(procedure.ret)
        valid = xdr.encode(reply_type, sample(reply_type, procedure.name))
        for _ in range(12):
            with contextlib.suppress(LibvirtPyError):
                xdr.decode(reply_type, mutate(generator, valid))
