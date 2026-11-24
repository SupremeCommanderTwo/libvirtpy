"""Operations on secrets."""

from libvirtpy.client.operations._common import (
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    one_handle,
)
from libvirtpy.client.references import (
    SecretRef,
    secret_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.secret import Secret

__all__ = [
    "define_secret",
    "get_secret_value",
    "list_secrets",
    "lookup_secret",
    "set_secret_value",
    "undefine_secret",
]


def lookup_secret(secret: SecretRef) -> Operation[Secret]:
    """Return the description of a secret (not its value).

    :param secret: a UUID, as text or ``UUID``, or a ``Secret`` model.
    :returns: the secret.
    :raises NoSecretError: if there is no such secret.
    """
    handle = yield from one_handle(secret_lookup(secret))
    return (yield from fetch_model("secret_get_xml_desc", handle, Secret))


def list_secrets() -> Operation[list[Secret]]:
    """Return the secrets.

    :returns: the secrets, without their values.
    """
    handles = yield from many_handles(
        Request("connect_list_all_secrets", {"need_results": 1, "flags": 0})
    )
    return (yield from fetch_models("secret_get_xml_desc", handles, Secret))


def define_secret(secret: Secret | str, *, flags: int = 0) -> Operation[Secret]:
    """Define (or redefine) a secret.

    :param secret: the description, as a model or XML text.
    :param flags: reserved, ``0``.
    :returns: the stored description, with the UUID libvirt chose if none was given.
    """
    xml = as_xml(secret)
    handle = yield from one_handle(
        Request("secret_define_xml", {"xml": xml, "flags": flags})
    )
    return (yield from fetch_model("secret_get_xml_desc", handle, Secret))


def undefine_secret(secret: SecretRef) -> Operation[None]:
    """Remove a secret and its value.

    :param secret: the secret.
    """
    handle = yield from one_handle(secret_lookup(secret))
    yield Request("secret_undefine", {"secret": handle})


def set_secret_value(secret: SecretRef, value: bytes) -> Operation[None]:
    """Store the value of a secret.

    :param secret: the secret.
    :param value: the value, e.g. a passphrase or a key.
    """
    handle = yield from one_handle(secret_lookup(secret))
    yield Request("secret_set_value", {"secret": handle, "value": value, "flags": 0})


def get_secret_value(secret: SecretRef) -> Operation[bytes]:
    """Read the value of a secret.

    :param secret: the secret.
    :returns: the value.
    :raises OperationInvalidError: if the secret is private.
    """
    handle = yield from one_handle(secret_lookup(secret))
    reply = yield Request("secret_get_value", {"secret": handle, "flags": 0})
    if not isinstance(reply, bytes):
        raise TypeError(f"expected bytes, got {reply!r}")
    return reply
