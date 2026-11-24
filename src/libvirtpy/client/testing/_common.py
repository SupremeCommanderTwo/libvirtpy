"""What the parts of the fake daemon share: types, samples and helpers."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, TypeVar
from uuid import uuid4

from libvirtpy.client.transport import Handle, Request
from libvirtpy.client.types import DomainState
from libvirtpy.rpc.protocol.procedures import PROCEDURES
from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml.storage import Pool, Volume


@dataclass
class _Entry[ModelT: LibvirtXmlModel]:
    model: ModelT
    active: bool = False
    autostart: bool = False
    transient: bool = False
    state: DomainState = DomainState.SHUTOFF
    secret_value: bytes | None = None


ModelT = TypeVar("ModelT", bound=LibvirtXmlModel)

Arguments = Mapping[str, object]

Action = Callable[[Arguments], object]

_START_PAUSED = 1

_CAPABILITIES = (
    "<capabilities><host><cpu><arch>x86_64</arch><model>fake</model></cpu></host>"
    "<guest><os_type>hvm</os_type><arch name='x86_64'><wordsize>64</wordsize>"
    "<domain type='kvm'/></arch></guest></capabilities>"
)

_DOMAIN_CAPABILITIES = (
    "<domainCapabilities><path>/usr/bin/qemu-system-x86_64</path><domain>kvm</domain>"
    "<arch>x86_64</arch><vcpu max='512'/></domainCapabilities>"
)

_POOL_CAPABILITIES = (
    "<storagepoolCapabilities><pool type='dir' supported='yes'/>"
    "<pool type='iscsi' supported='no'/></storagepoolCapabilities>"
)

_SYSINFO = (
    "<sysinfo type='smbios'><system><entry name='manufacturer'>Fake Inc.</entry>"
    "</system></sysinfo>"
)

_PCI_DEVICE = (
    "<device><name>pci_0000_00_1f_2</name><capability type='pci'><domain>0</domain>"
    "<bus>0</bus><slot>31</slot><function>2</function><product id='0x2922'/>"
    "<vendor id='0x8086'/></capability></device>"
)

_PROCEDURES_BY_NAME = {p.name: p for p in PROCEDURES.values()}

_SNAPSHOT_STATES: dict[DomainState, Literal["running", "paused", "shutoff"]] = {
    DomainState.RUNNING: "running",
    DomainState.PAUSED: "paused",
    DomainState.SHUTOFF: "shutoff",
}


def _check_against_protocol(request: Request) -> None:
    """Fail if the request does not match the real procedure's arguments.

    This keeps the fake faithful to the wire: whatever works against it names
    real procedures with their real argument names.

    :param request: the request to check.
    :raises TypeError: if the procedure is unknown or the arguments differ.
    """
    procedure = _PROCEDURES_BY_NAME.get(request.procedure)
    if procedure is None:
        raise TypeError(f"{request.procedure} is not a libvirt procedure")

    expected = (
        sorted(name for name, _ in procedure.args.xdr_fields) if procedure.args else []
    )
    if sorted(request.arguments) != expected:
        raise TypeError(
            f"{request.procedure} takes {expected}, got {sorted(request.arguments)}"
        )


def _redefine[ModelT: LibvirtXmlModel](
    entry: _Entry[ModelT], model: ModelT
) -> _Entry[ModelT]:
    entry.model = model
    return entry


def _key_of(model: LibvirtXmlModel) -> str:
    uuid_text = getattr(model, "uuid", None)
    name = getattr(model, "name", None)
    if isinstance(name, str):
        return name
    if isinstance(uuid_text, str):
        return uuid_text
    raise TypeError(f"{model!r} has neither a name nor a UUID")


def _handle_of(model: LibvirtXmlModel) -> Handle:
    uuid_text = getattr(model, "uuid", None)
    name = getattr(model, "name", None)
    return Handle(
        name=name if isinstance(name, str) else str(uuid_text),
        uuid=uuid_text if isinstance(uuid_text, str) else None,
        id=getattr(model, "id", None),
    )


def _ensure_uuid(model: LibvirtXmlModel) -> None:
    if "uuid" in type(model).model_fields and getattr(model, "uuid", None) is None:
        model.__setattr__("uuid", str(uuid4()))


def _pool_name(pool: Pool) -> str:
    if pool.name is None:
        raise TypeError("the pool has no name")
    return pool.name


def _volume_handle(volume: Volume, pool: str) -> Handle:
    return Handle(name=volume.name, parent=pool)


def _xml_of(model: LibvirtXmlModel) -> str:
    text = model.to_xml(encoding="unicode")
    if not isinstance(text, str):
        raise TypeError("to_xml(encoding='unicode') did not return text")
    return text


def _device_identity(device: object) -> str | None:
    target = getattr(device, "target", None)
    mac = getattr(device, "mac", None)
    for candidate in (getattr(target, "dev", None), getattr(mac, "address", None)):
        if isinstance(candidate, str):
            return candidate
    return None


def _handle_argument(arguments: Arguments) -> Handle:
    for value in arguments.values():
        if isinstance(value, Handle):
            return value
    raise TypeError("the request has no object handle")


def _text(arguments: Arguments, name: str) -> str:
    value = arguments[name]
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text, got {value!r}")
    return value


def _int(arguments: Arguments, name: str) -> int:
    value = arguments[name]
    if not isinstance(value, int):
        raise TypeError(f"{name} must be a number, got {value!r}")
    return value
