"""Operations that find secrets by what they are used for."""

from libvirtpy.client.operations._common import fetch_model, one_handle
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.secret import Secret

__all__ = ["lookup_secret_by_usage"]


def lookup_secret_by_usage(usage_type: int, usage_id: str) -> Operation[Secret]:
    """Find a secret by its usage.

    :param usage_type: ``virSecretUsageType``: 1 volume, 2 ceph, 3 iscsi, 4 tls,
        5 vtpm.
    :param usage_id: the usage identifier: a volume path, a ceph user name, ...
    :returns: the secret.
    :raises NoSecretError: if there is none.
    """
    found = yield from one_handle(
        Request(
            "secret_lookup_by_usage", {"usage_type": usage_type, "usage_id": usage_id}
        )
    )
    return (yield from fetch_model("secret_get_xml_desc", found, Secret))
