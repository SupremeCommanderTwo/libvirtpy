"""A transport that answers any request with a sample built from the real protocol.

For each request it converts the arguments with ``wire.convert_arguments`` and
encodes them with the XDR codec (so a wrong argument name, type or limit fails),
then builds a reply from the procedure's return struct and converts it with
``wire.convert_reply``. It knows nothing about libvirt's behaviour: it proves
that an operation speaks the real protocol and understands the shape of the
real replies.
"""

from typing import Any, cast

from libvirtpy.client.transport import Request
from libvirtpy.client.wire import convert_arguments, convert_reply
from libvirtpy.rpc import xdr
from libvirtpy.rpc.protocol.procedures import PROCEDURES
from libvirtpy.rpc.session import StreamEvent
from libvirtpy.rpc.stream import RemoteStream

PROCEDURES_BY_NAME = {p.name: p for p in PROCEDURES.values()}

DOMAIN = "<domain type='kvm'><name>vm</name></domain>"
XML_REPLIES = {
    "domain": DOMAIN,
    "network": "<network><name>net</name></network>",
    "pool": "<pool type='dir'><name>pool</name></pool>",
    "volume": "<volume><name>vol</name></volume>",
    "secret": "<secret><usage type='volume'><volume>/v</volume></usage></secret>",
    "nwfilter": "<filter name='f'/>",
    "interface": "<interface type='ethernet' name='eth0'/>",
    "device": (
        "<device><name>pci_0000_00_1f_2</name><capability type='pci'>"
        "<domain>0</domain><bus>0</bus><slot>31</slot><function>2</function>"
        "<product id='0x2922'/><vendor id='0x8086'/></capability></device>"
    ),
    "snapshot": "<domainsnapshot><name>s</name></domainsnapshot>",
    "checkpoint": "<domaincheckpoint><name>c</name></domaincheckpoint>",
    "port": (
        "<networkport><uuid>01234567-89ab-cdef-0123-456789abcdef</uuid>"
        "<owner><name>vm</name><uuid>01234567-89ab-cdef-0123-456789abcdef</uuid></owner>"
        "<mac address='52:54:00:00:00:01'/><group>g</group></networkport>"
    ),
    "binding": (
        "<filterbinding><owner><name>vm</name>"
        "<uuid>01234567-89ab-cdef-0123-456789abcdef</uuid></owner>"
        "<portdev name='tap0'/><mac address='52:54:00:00:00:01'/>"
        "<filterref filter='f'/></filterbinding>"
    ),
    "backup": "<domainbackup/>",
    "capabilities": (
        "<capabilities><host><cpu><arch>x86_64</arch></cpu></host></capabilities>"
    ),
    "domaincaps": (
        "<domainCapabilities><path>/x</path><domain>kvm</domain>"
        "<arch>x86_64</arch></domainCapabilities>"
    ),
    "poolcaps": "<storagepoolCapabilities/>",
    "sysinfo": "<sysinfo type='smbios'/>",
}

# Procedure -> which XML to answer a text field with.
XML_PROCEDURES = {
    "connect_get_capabilities": "capabilities",
    "connect_get_domain_capabilities": "domaincaps",
    "connect_get_storage_pool_capabilities": "poolcaps",
    "connect_get_sysinfo": "sysinfo",
    "node_get_sysinfo": "sysinfo",
    "connect_domain_xml_from_native": "domain",
}
XML_KINDS = (
    ("domain_snapshot", "snapshot"),
    ("domain_checkpoint", "checkpoint"),
    ("domain_backup", "backup"),
    ("network_port", "port"),
    ("nwfilter_binding", "binding"),
    ("storage_pool", "pool"),
    ("storage_vol", "volume"),
    ("node_device", "device"),
    ("domain", "domain"),
    ("network", "network"),
    ("secret", "secret"),
    ("nwfilter", "nwfilter"),
    ("interface", "interface"),
)


class NullRpc:
    """A connection that accepts stream packets and confirms the end at once."""

    def __init__(self) -> None:
        """Create a connection that has no stream yet."""
        self.stream: RemoteStream | None = None

    def send_stream_data(self, serial: int, data: bytes) -> None:
        """Ignore data."""

    def finish_stream(self, serial: int) -> None:
        """Confirm the end, as a daemon does."""
        if self.stream is not None:
            self.stream.deliver(StreamEvent(serial, "closed"))

    def abort_stream(self, serial: int) -> None:
        """Ignore the abort."""


class SyntheticDaemon:
    """Serves every request with a sample reply, and records what it saw."""

    def __init__(self) -> None:
        """Create a daemon that has served nothing yet."""
        self.requests: list[Request] = []

    def call(self, request: Request) -> object:
        """Check a request against the real protocol and answer it.

        :param request: the call.
        :returns: the reply, converted as the wire transport would.
        :raises KeyError: if the procedure does not exist.
        """
        self.requests.append(request)
        procedure = PROCEDURES_BY_NAME[request.procedure]

        arguments = convert_arguments(procedure, request.arguments)
        if procedure.args is not None:
            xdr.encode(xdr.StructType(procedure.args), arguments)
        if request.stream is not None:
            rpc = NullRpc()
            rpc.stream = RemoteStream(cast(Any, rpc), request.stream)
            return rpc.stream

        if procedure.ret is None:
            return None
        reply = sample(xdr.StructType(procedure.ret), request.procedure)
        xdr.encode(xdr.StructType(procedure.ret), reply)
        return convert_reply(procedure, reply)

    def close(self) -> None:
        """Close the connection (nothing to do)."""


def sample(xdr_type: Any, procedure: str, depth: int = 0) -> Any:
    """Build a small value of a descriptor's type.

    :param xdr_type: the descriptor.
    :param procedure: the procedure the value is a reply of, to pick XML for.
    :param depth: how deep in the structure we are.
    :returns: a value that encodes.
    """
    if isinstance(xdr_type, xdr.String):
        return _text_sample(procedure)
    if isinstance(xdr_type, xdr.VarOpaque):
        return b"ab"
    if isinstance(xdr_type, xdr.FixedOpaque):
        return bytes(range(xdr_type.size))
    if isinstance(xdr_type, xdr.Array):
        return [sample(xdr_type.item, procedure, depth + 1)] if depth < 3 else []
    if isinstance(xdr_type, xdr.FixedArray):
        return [sample(xdr_type.item, procedure, depth + 1)] * xdr_type.size
    if isinstance(xdr_type, xdr.OptionalOf):
        return sample(xdr_type.item, procedure, depth + 1) if depth == 0 else None
    return _structured_sample(xdr_type, procedure, depth)


def _structured_sample(xdr_type: Any, procedure: str, depth: int) -> Any:
    """Build a sample of an enum, struct, union or number.

    :param xdr_type: the descriptor.
    :param procedure: the procedure the value is a reply of.
    :param depth: how deep in the structure we are.
    :returns: the value.
    """
    if isinstance(xdr_type, xdr.EnumType):
        return next(iter(xdr_type.enum))
    if isinstance(xdr_type, xdr.StructType):
        fields = {
            n: sample(t, procedure, depth + 1) for n, t in xdr_type.cls.xdr_fields
        }
        return xdr_type.cls(**fields)
    if isinstance(xdr_type, xdr.UnionType):
        label, arm = next(iter(xdr_type.cls.xdr_arms.items()))
        name, _ = xdr_type.cls.xdr_discriminant
        value = None if arm is None else sample(arm, procedure, depth + 1)
        return xdr_type.cls(**{name: label, "value": value})
    fmt = getattr(xdr_type, "fmt", None)
    if fmt in (">f", ">d"):
        return 0.5
    return 1 if fmt else True


def _text_sample(procedure: str) -> str:
    """Pick the text a reply field holds: XML for XML procedures, else a word.

    :param procedure: the procedure the text is a reply of.
    :returns: the text.
    """
    kind = XML_PROCEDURES.get(procedure)
    if kind is None and procedure.endswith(("xml_desc", "native")):
        kind = next(
            (k for prefix, k in XML_KINDS if procedure.startswith(prefix)), None
        )
    if procedure.startswith(("domain_save_image", "domain_managed_save")):
        kind = "domain"
    return XML_REPLIES[kind] if kind else "ab"
