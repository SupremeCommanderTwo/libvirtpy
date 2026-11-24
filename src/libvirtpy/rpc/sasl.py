"""SASL authentication for libvirt daemons (pure Python, standard library only).

Supported mechanisms, best first: SCRAM-SHA-256, SCRAM-SHA-1, DIGEST-MD5 (what
libvirt's default configuration uses) and PLAIN. None of them needs a SASL
*security layer*, so SASL is allowed only on a channel that is already
protected: a UNIX socket, TLS or SSH. GSSAPI (Kerberos) is not supported.

``sasl_exchange`` is a generator that yields the calls to make and receives
their replies, so the sync and the async client drive the same code.
"""

import base64
import hashlib
import hmac
import re
import secrets
import unicodedata
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Protocol

from libvirtpy.rpc.errors import AuthFailedError, ErrorNumber
from libvirtpy.rpc.procedure import Procedure
from libvirtpy.rpc.protocol import procedures, types

__all__ = [
    "DigestMd5",
    "PlainMechanism",
    "SaslCredentials",
    "SaslMechanism",
    "Scram",
    "choose_mechanism",
    "parse_mechanisms",
    "sasl_exchange",
]

SERVICE = "libvirt"
CHAR_LIMIT = 128
MAX_ITERATIONS = 1_000_000
SaslCall = tuple[Procedure[Any, Any], Any]


@dataclass(frozen=True)
class SaslCredentials:
    """The user name and password to authenticate with."""

    username: str
    password: str
    realm: str | None = None
    """The realm to use if the server does not name one (DIGEST-MD5)."""


class SaslMechanism(Protocol):
    """One authentication mechanism, as a client."""

    name: str

    @property
    def finished(self) -> bool:
        """Whether the server has proved itself and nothing more is expected."""

    def start(self) -> bytes | None:
        """Make the first message.

        :returns: the initial response, or ``None`` if the server speaks first.
        """

    def step(self, challenge: bytes) -> bytes | None:
        """Answer a message of the server.

        :param challenge: the server's data.
        :returns: the response, or ``None`` for no data.
        :raises AuthFailedError: if the server's data is wrong.
        """


class PlainMechanism:
    """PLAIN (RFC 4616): user name and password in the clear."""

    name = "PLAIN"

    def __init__(self, credentials: SaslCredentials) -> None:
        """Create the mechanism.

        :param credentials: who to authenticate as.
        """
        self._credentials = credentials

    @property
    def finished(self) -> bool:
        """PLAIN has nothing to verify, so it is always finished."""
        return True

    def start(self) -> bytes | None:
        """Make the initial response.

        :returns: ``authzid NUL user NUL password`` with an empty authzid.
        """
        user = self._credentials.username.encode()
        password = self._credentials.password.encode()
        return b"\0" + user + b"\0" + password

    def step(self, challenge: bytes) -> bytes | None:
        """Refuse any server message: PLAIN has none.

        :param challenge: the server's data.
        :returns: nothing.
        :raises AuthFailedError: always.
        """
        raise _failure("the server sent data during PLAIN")


class Scram:
    """SCRAM-SHA-1 and SCRAM-SHA-256 (RFC 5802, RFC 7677), without channel binding."""

    def __init__(
        self, credentials: SaslCredentials, algorithm: str, nonce: str | None = None
    ) -> None:
        """Create the mechanism.

        :param credentials: who to authenticate as.
        :param algorithm: ``sha1`` or ``sha256``.
        :param nonce: our random string; made up if left out (tests fix it).
        """
        self.name = f"SCRAM-{algorithm.upper().replace('SHA', 'SHA-')}"
        self._credentials = credentials
        self._algorithm = algorithm
        self._nonce = nonce or secrets.token_urlsafe(18)

        self._bare = ""
        self._server_first = ""
        self._expected_signature = b""
        self._stage = 0

    @property
    def finished(self) -> bool:
        """Whether the server's signature was checked."""
        return self._stage == 2

    def start(self) -> bytes | None:
        """Make the client-first message.

        :returns: the message with the gs2 header ``n,,``.
        """
        user = _prepare(self._credentials.username)
        user = user.replace("=", "=3D").replace(",", "=2C")
        self._bare = f"n={user},r={self._nonce}"
        return f"n,,{self._bare}".encode()

    def step(self, challenge: bytes) -> bytes | None:
        """Answer the server-first message, or check the server-final one.

        :param challenge: the server's data.
        :returns: the client-final message, or nothing after the last check.
        :raises AuthFailedError: if the server's data is wrong.
        """
        if self._stage == 0:
            self._stage = 1
            return self._client_final(_text(challenge))

        self._verify(_text(challenge))
        self._stage = 2
        return None

    def _client_final(self, server_first: str) -> bytes:
        """Compute the client-final message with its proof.

        :param server_first: the server's first message.
        :returns: the client-final message.
        :raises AuthFailedError: if the server's nonce or parameters are wrong.
        """
        fields = {
            key: value
            for key, _, value in (
                part.partition("=") for part in server_first.split(",")
            )
        }
        nonce = fields.get("r", "")
        if not nonce.startswith(self._nonce) or "s" not in fields or "i" not in fields:
            raise _failure("the SCRAM server-first message is not valid")

        salt = _base64(fields["s"])
        iterations = _iterations(fields["i"])

        password = _prepare(self._credentials.password).encode()
        salted = hashlib.pbkdf2_hmac(self._algorithm, password, salt, iterations)
        client_key = self._hmac(salted, b"Client Key")
        without_proof = f"c=biws,r={nonce}"

        message = f"{self._bare},{server_first},{without_proof}".encode()

        stored_key = hashlib.new(self._algorithm, client_key).digest()
        signature = self._hmac(stored_key, message)
        proof = bytes(a ^ b for a, b in zip(client_key, signature, strict=True))
        self._expected_signature = self._hmac(
            self._hmac(salted, b"Server Key"), message
        )
        return f"{without_proof},p={base64.b64encode(proof).decode()}".encode()

    def _verify(self, server_final: str) -> None:
        """Check the server's signature.

        :param server_final: the server's last message (``v=...``).
        :raises AuthFailedError: if the server reports an error or its proof is wrong.
        """
        if server_final.startswith("e="):
            raise _failure(f"the server refused the credentials: {server_final[2:]}")

        proof = _base64(server_final.removeprefix("v="))
        if not hmac.compare_digest(proof, self._expected_signature):
            raise _failure("the server could not prove it knows the password")

    def _hmac(self, key: bytes, message: bytes) -> bytes:
        """Compute an HMAC with the mechanism's hash.

        :param key: the key.
        :param message: the data.
        :returns: the digest.
        """
        return hmac.new(key, message, self._algorithm).digest()


class DigestMd5:
    """DIGEST-MD5 (RFC 2831), authentication only (``qop=auth``)."""

    name = "DIGEST-MD5"

    def __init__(
        self,
        credentials: SaslCredentials,
        host: str,
        cnonce: str | None = None,
        service: str = SERVICE,
    ) -> None:
        """Create the mechanism.

        :param credentials: who to authenticate as.
        :param host: the server's host name, for the ``digest-uri``.
        :param cnonce: our random string; made up if left out (tests fix it).
        :param service: the service name in the ``digest-uri``; libvirt's is
            ``libvirt``.
        """
        self._credentials = credentials
        self._digest_uri = f"{service}/{host}"
        self._cnonce = cnonce or secrets.token_hex(16)
        self._expected_rspauth = ""
        self._stage = 0

    @property
    def finished(self) -> bool:
        """Whether the server's ``rspauth`` was checked."""
        return self._stage == 2

    def start(self) -> bytes | None:
        """DIGEST-MD5 has no initial response: the server speaks first.

        :returns: nothing.
        """
        return None

    def step(self, challenge: bytes) -> bytes | None:
        """Answer the server's challenge, or check its ``rspauth``.

        :param challenge: the server's data.
        :returns: the response; empty after the last check.
        :raises AuthFailedError: if the server's data is wrong.
        """
        if self._stage == 0:
            self._stage = 1
            return self._respond(_directives(_text(challenge)))

        rspauth = _directives(_text(challenge)).get("rspauth")
        if rspauth != self._expected_rspauth:
            raise _failure("the server could not prove it knows the password")
        self._stage = 2
        return b""

    def _respond(self, challenge: dict[str, str]) -> bytes:
        """Compute the response to the server's challenge.

        :param challenge: its directives (``realm``, ``nonce``, ``qop``, ...).
        :returns: the response directives.
        :raises AuthFailedError: if the server offers no ``auth`` quality of protection.
        """
        if "auth" not in challenge.get("qop", "auth").split(","):
            raise _failure("the server demands a SASL security layer, not supported")

        realm = challenge.get("realm", self._credentials.realm or "")
        nonce = challenge.get("nonce")
        if nonce is None:
            raise _failure("the DIGEST-MD5 challenge has no nonce")
        user = self._credentials.username

        secret = hashlib.md5(
            f"{user}:{realm}:{self._credentials.password}".encode()
        ).digest()
        key = hashlib.md5(secret + f":{nonce}:{self._cnonce}".encode()).hexdigest()

        response = self._digest(key, nonce, "AUTHENTICATE")
        self._expected_rspauth = self._digest(key, nonce, "")

        return (
            f'username="{user}",realm="{realm}",nonce="{nonce}",'
            f'cnonce="{self._cnonce}",nc=00000001,qop=auth,'
            f'digest-uri="{self._digest_uri}",response={response},charset=utf-8'
        ).encode()

    def _digest(self, key: str, nonce: str, method: str) -> str:
        """Compute the ``response`` (or ``rspauth``, with an empty method) value.

        :param key: the hex MD5 of ``A1``.
        :param nonce: the server's nonce.
        :param method: ``AUTHENTICATE`` for the response, empty for ``rspauth``.
        :returns: the 32 hex digits.
        """
        a2 = hashlib.md5(f"{method}:{self._digest_uri}".encode()).hexdigest()
        data = f"{key}:{nonce}:00000001:{self._cnonce}:auth:{a2}"
        return hashlib.md5(data.encode()).hexdigest()


def choose_mechanism(
    offered: list[str], credentials: SaslCredentials, host: str
) -> SaslMechanism:
    """Pick the best mechanism both sides support.

    :param offered: the mechanisms the server lists.
    :param credentials: who to authenticate as.
    :param host: the server's host name.
    :returns: the mechanism.
    :raises AuthFailedError: if the server offers none of ours.
    """
    candidates: list[tuple[str, SaslMechanism]] = [
        ("SCRAM-SHA-256", Scram(credentials, "sha256")),
        ("SCRAM-SHA-1", Scram(credentials, "sha1")),
        ("DIGEST-MD5", DigestMd5(credentials, host)),
        ("PLAIN", PlainMechanism(credentials)),
    ]
    for name, mechanism in candidates:
        if name in offered:
            return mechanism
    raise _failure(f"no common SASL mechanism: the server offers {offered}")


def parse_mechanisms(offered: str) -> list[str]:
    """Split the mechanism list that a daemon sends.

    libvirt separates the names with commas (``SCRAM-SHA-256,DIGEST-MD5``); SASL
    itself uses spaces, so both are accepted.

    :param offered: the daemon's ``mechlist`` string.
    :returns: the mechanism names, in the order the daemon gave them.
    """
    return [name for name in re.split(r"[,\s]+", offered) if name]


def sasl_exchange(credentials: SaslCredentials, host: str) -> Generator[SaslCall, Any]:
    """Run the SASL conversation with a daemon.

    :param credentials: who to authenticate as.
    :param host: the server's host name.
    :returns: a generator that yields ``(procedure, arguments)`` and receives the
        reply of each call.
    :raises AuthFailedError: if the mechanisms do not match or the server's proof fails.
    """
    init = yield procedures.AUTH_SASL_INIT, None
    mechanism = choose_mechanism(parse_mechanisms(init.mechlist), credentials, host)

    first = mechanism.start()
    start = types.AuthSaslStartArgs(
        mech=mechanism.name, nil=int(first is None), data=_to_chars(first)
    )
    reply = yield procedures.AUTH_SASL_START, start

    while not reply.complete:
        answer = mechanism.step(_from_chars(reply.data))
        step = types.AuthSaslStepArgs(nil=int(answer is None), data=_to_chars(answer))
        reply = yield procedures.AUTH_SASL_STEP, step

    final = _from_chars(reply.data)
    if final and not mechanism.finished:
        mechanism.step(final)


def _to_chars(data: bytes | None) -> list[int]:
    """Make the wire form of data: an array of signed ``char``.

    :param data: bytes, or ``None``.
    :returns: one signed integer per byte.
    """
    return [byte - 256 if byte >= CHAR_LIMIT else byte for byte in data or b""]


def _from_chars(chars: list[int]) -> bytes:
    """Make bytes from the wire form (an array of signed ``char``).

    :param chars: the integers.
    :returns: the bytes.
    """
    return bytes(char & 0xFF for char in chars)


def _text(data: bytes) -> str:
    """Read a server message as text.

    :param data: the bytes the server sent.
    :returns: the text.
    :raises AuthFailedError: if it is not UTF-8.
    """
    try:
        return data.decode()
    except UnicodeDecodeError as error:
        raise _failure("the server's SASL message is not text") from error


def _base64(text: str) -> bytes:
    """Decode base64 sent by the server.

    :param text: the base64 text.
    :returns: the bytes.
    :raises AuthFailedError: if it is not valid base64.
    """
    try:
        return base64.b64decode(text, validate=True)
    except ValueError as error:
        raise _failure("the server's SASL message has invalid base64") from error


def _iterations(text: str) -> int:
    """Read the SCRAM iteration count, refusing values that would freeze us.

    :param text: the ``i=`` value.
    :returns: the count.
    :raises AuthFailedError: if it is not a number from 1 to ``MAX_ITERATIONS``.
    """
    if not text.isdigit() or not 1 <= int(text) <= MAX_ITERATIONS:
        raise _failure(f"the SCRAM iteration count {text[:12]!r} is not acceptable")
    return int(text)


def _directives(text: str) -> dict[str, str]:
    """Parse ``key=value,key="quoted value"`` directives.

    :param text: the server's challenge.
    :returns: the directives; the first of a repeated key wins.
    """
    found: dict[str, str] = {}
    for key, quoted, plain in re.findall(r'([\w-]+)=(?:"([^"]*)"|([^,]*))', text):
        found.setdefault(key, quoted or plain)
    return found


def _prepare(text: str) -> str:
    """Normalise a user name or password (an approximation of SASLprep).

    :param text: the text.
    :returns: the text in Unicode normal form KC.
    """
    return unicodedata.normalize("NFKC", text)


def _failure(message: str) -> AuthFailedError:
    """Make the error for a failed authentication.

    :param message: what went wrong.
    :returns: the exception.
    """
    return AuthFailedError(message, code=ErrorNumber.AUTH_FAILED)
