"""Round-trip real XML: parse it with the models, write it back, compare.

The corpus of libvirt's own test files proves the models on files that libvirt's
authors wrote. This checks the XML a real daemon produces, which has details
nobody wrote by hand (aliases, addresses, security labels, runtime ids).
"""

from collections.abc import Iterable
from dataclasses import dataclass

from libvirtpy.client import LibvirtClient
from libvirtpy.client.transport import Handle, Request
from libvirtpy.xml._base import LibvirtXmlModel
from tests.helpers.xmlcompare import differences


@dataclass(frozen=True)
class Document:
    """One XML document and the model that should read and write it."""

    label: str
    xml: str
    model: type[LibvirtXmlModel]


def problems(documents: Iterable[Document]) -> list[str]:
    """Round-trip documents and describe each one that does not survive.

    :param documents: what to check.
    :returns: one line per problem: the document, then the first differences.
    """
    found = []
    for document in documents:
        try:
            written = document.model.from_xml(document.xml).to_xml(encoding="unicode")
        except Exception as error:  # any failure is a finding
            found.append(f"{document.label}: cannot parse: {str(error)[:200]}")
            continue

        first = list(differences(document.xml, str(written)))[:5]
        if first:
            found.append(f"{document.label}: {'; '.join(first)}")
    return found


def fetch(client: LibvirtClient, procedure: str, **arguments: object) -> object:
    """Make a raw call and return what the wire transport converts the reply to.

    :param client: a client connected to a real daemon.
    :param procedure: the libvirt procedure name.
    :param arguments: its arguments by name.
    :returns: the converted reply (a handle, a list of handles, text...).
    """
    transport = client._transport  # the raw wire, which tests use on purpose
    return transport.call(Request(procedure, arguments))


def xml_of(client: LibvirtClient, procedure: str, **arguments: object) -> str:
    """Make a raw call that returns XML text.

    :param client: a client connected to a real daemon.
    :param procedure: the libvirt procedure name.
    :param arguments: its arguments by name.
    :returns: the XML the daemon sent.
    """
    reply = fetch(client, procedure, **arguments)
    assert isinstance(reply, str)
    return reply


def listing(client: LibvirtClient, procedure: str, **arguments: object) -> list[Handle]:
    """Make a raw ``*_list_all_*`` call.

    :param client: a client connected to a real daemon.
    :param procedure: the libvirt procedure name.
    :param arguments: its arguments by name (``need_results`` and ``flags`` are added).
    :returns: the handles of the objects.
    """
    reply = fetch(client, procedure, need_results=1, flags=0, **arguments)
    assert isinstance(reply, list)
    return reply
