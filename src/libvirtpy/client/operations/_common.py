"""Helpers shared by the operation modules (private)."""

from collections.abc import Callable, Iterator
from functools import partial
from typing import TypeVar

from libvirtpy.client.references import (
    CheckpointRef,
    DomainRef,
    HostInterfaceRef,
    NetworkPortRef,
    NetworkRef,
    NodeDeviceRef,
    NwFilterBindingRef,
    NwFilterRef,
    PoolRef,
    SecretRef,
    SnapshotRef,
    VolumeRef,
    checkpoint_lookup,
    domain_lookup,
    host_interface_lookup,
    network_lookup,
    network_port_lookup,
    node_device_lookup,
    nwfilter_binding_lookup,
    nwfilter_lookup,
    pool_lookup,
    secret_lookup,
    snapshot_lookup,
    volume_lookup,
)
from libvirtpy.client.transport import Handle, Operation, Request
from libvirtpy.rpc import typed_params
from libvirtpy.rpc.protocol.types import TypedParam
from libvirtpy.rpc.typed_params import TypedValue
from libvirtpy.xml._base import LibvirtXmlModel

ModelT = TypeVar("ModelT", bound=LibvirtXmlModel)
StructT = TypeVar("StructT")


DOMAINS_ACTIVE, DOMAINS_INACTIVE = 1, 2


INACTIVE, ACTIVE = 1, 2


OBJECT_FIELDS = {
    "domain_get_xml_desc": "dom",
    "network_get_xml_desc": "net",
    "storage_pool_get_xml_desc": "pool",
    "storage_vol_get_xml_desc": "vol",
    "secret_get_xml_desc": "secret",
    "nwfilter_get_xml_desc": "nwfilter",
    "interface_get_xml_desc": "iface",
    "node_device_get_xml_desc": "name",
    "domain_snapshot_get_xml_desc": "snap",
    "domain_checkpoint_get_xml_desc": "checkpoint",
    "network_port_get_xml_desc": "port",
    "nwfilter_binding_get_xml_desc": "nwfilter",
}


"""The argument that names the object, in each ``*_get_xml_desc`` procedure."""


def one_handle(request: Request) -> Operation[Handle]:
    """Send ``request`` and expect one object handle back.

    :param request: the request.
    :returns: the handle in the reply.
    """
    reply = yield request
    if not isinstance(reply, Handle):
        raise TypeError(f"expected a Handle for {request.procedure}, got {reply!r}")
    return reply


def many_handles(request: Request) -> Operation[list[Handle]]:
    """Send ``request`` and expect a list of object handles back.

    :param request: the request.
    :returns: the handles in the reply.
    """
    reply = yield request
    if not isinstance(reply, list) or not all(isinstance(h, Handle) for h in reply):
        raise TypeError(f"expected Handles for {request.procedure}, got {reply!r}")
    return list(_iterate_handles(reply))


def fetch_model[ModelT: LibvirtXmlModel](
    procedure: str, handle: Handle, model_type: type[ModelT]
) -> Operation[ModelT]:
    """Ask for the XML of an object and parse it.

    :param procedure: the ``*_get_xml_desc`` procedure of the object kind.
    :param handle: the object.
    :param model_type: the model class to parse the XML with.
    :returns: the parsed model.
    """
    field = OBJECT_FIELDS[procedure]
    xml = as_text((yield Request(procedure, {field: handle, "flags": 0})))
    return model_type.from_xml(xml)


def fetch_models[ModelT: LibvirtXmlModel](
    procedure: str, handles: list[Handle], model_type: type[ModelT]
) -> Operation[list[ModelT]]:
    """Fetch several objects, one request each.

    :param procedure: the ``*_get_xml_desc`` procedure of the object kind.
    :param handles: the objects.
    :param model_type: the model class to parse the XML with.
    :returns: the models, in the order of ``handles``.
    """
    models = []
    for handle in handles:
        models.append(  # noqa: PERF401  (a yield from cannot be a comprehension)
            (yield from fetch_model(procedure, handle, model_type))
        )
    return models


def as_text(reply: object) -> str:
    """Check that a reply is text.

    :param reply: what the daemon sent.
    :returns: the text.
    :raises TypeError: if it is not text.
    """
    if not isinstance(reply, str):
        raise TypeError(f"expected text, got {reply!r}")
    return reply


def as_int(reply: object) -> int:
    """Check that a reply is a number.

    :param reply: what the daemon sent.
    :returns: the number.
    :raises TypeError: if it is not a number.
    """
    if not isinstance(reply, int) or isinstance(reply, bool):
        raise TypeError(f"expected a number, got {reply!r}")
    return reply


def as_xml(value: LibvirtXmlModel | str) -> str:
    """Turn a model into XML text; text passes through.

    :param value: a model or XML text.
    :returns: the XML text.
    """
    if isinstance(value, str):
        return value
    text = value.to_xml(encoding="unicode")
    if not isinstance(text, str):
        raise TypeError("to_xml(encoding='unicode') did not return text")
    return text


def _iterate_handles(replies: list[object]) -> Iterator[Handle]:
    """Yield the handles among the replies.

    :param replies: the items of a list reply.
    :returns: the items that are handles.
    """
    for reply in replies:
        if isinstance(reply, Handle):
            yield reply


def on_object(
    lookup: Request, field: str, procedure: str, arguments: dict[str, object]
) -> Operation[object]:
    """Find an object, then call a procedure on it.

    :param lookup: the request that finds the object.
    :param field: the argument of ``procedure`` that names the object.
    :param procedure: the procedure to call.
    :param arguments: its other arguments.
    :returns: the daemon's reply.
    """
    handle = yield from one_handle(lookup)
    return (yield Request(procedure, {field: handle, **arguments}))


def on_domain(
    domain: DomainRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a domain.

    :param domain: the domain.
    :param procedure: the procedure; the domain is its ``dom`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    return (yield from on_object(domain_lookup(domain), "dom", procedure, arguments))


def on_network(
    network: NetworkRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a network.

    :param network: the network.
    :param procedure: the procedure; the network is its ``net`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    return (yield from on_object(network_lookup(network), "net", procedure, arguments))


def on_pool(pool: PoolRef, procedure: str, **arguments: object) -> Operation[object]:
    """Call a procedure on a storage pool.

    :param pool: the pool.
    :param procedure: the procedure; the pool is its ``pool`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    return (yield from on_object(pool_lookup(pool), "pool", procedure, arguments))


def on_volume(
    pool: PoolRef, volume: VolumeRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a storage volume.

    :param pool: the pool of the volume.
    :param volume: the volume.
    :param procedure: the procedure; the volume is its ``vol`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    pool_handle = yield from one_handle(pool_lookup(pool))
    lookup = volume_lookup(pool_handle, volume)
    return (yield from on_object(lookup, "vol", procedure, arguments))


def on_snapshot(
    domain: DomainRef, snapshot: SnapshotRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a snapshot of a domain.

    :param domain: the domain.
    :param snapshot: the snapshot.
    :param procedure: the procedure; the snapshot is its ``snap`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    domain_handle = yield from one_handle(domain_lookup(domain))
    lookup = snapshot_lookup(domain_handle, snapshot)
    return (yield from on_object(lookup, "snap", procedure, arguments))


def on_secret(
    secret: SecretRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a secret.

    :param secret: the secret.
    :param procedure: the procedure; the secret is its ``secret`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    return (yield from on_object(secret_lookup(secret), "secret", procedure, arguments))


def on_nwfilter(
    nwfilter: NwFilterRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a network filter.

    :param nwfilter: the filter.
    :param procedure: the procedure; the filter is its ``nwfilter`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    lookup = nwfilter_lookup(nwfilter)
    return (yield from on_object(lookup, "nwfilter", procedure, arguments))


def on_host_interface(
    interface: HostInterfaceRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a network interface of the host.

    :param interface: the interface.
    :param procedure: the procedure; the interface is its ``iface`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    lookup = host_interface_lookup(interface)
    return (yield from on_object(lookup, "iface", procedure, arguments))


def on_node_device(
    device: NodeDeviceRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a host device.

    :param device: the device.
    :param procedure: the procedure; the device is its ``name`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    lookup = node_device_lookup(device)
    return (yield from on_object(lookup, "name", procedure, arguments))


def on_checkpoint(
    domain: DomainRef, checkpoint: CheckpointRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a checkpoint of a domain.

    :param domain: the domain.
    :param checkpoint: the checkpoint.
    :param procedure: the procedure; the checkpoint is its ``checkpoint`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    domain_handle = yield from one_handle(domain_lookup(domain))
    lookup = checkpoint_lookup(domain_handle, checkpoint)
    return (yield from on_object(lookup, "checkpoint", procedure, arguments))


def on_network_port(
    network: NetworkRef, port: NetworkPortRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a port of a network.

    :param network: the network.
    :param port: the port.
    :param procedure: the procedure; the port is its ``port`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    network_handle = yield from one_handle(network_lookup(network))
    lookup = network_port_lookup(network_handle, port)
    return (yield from on_object(lookup, "port", procedure, arguments))


def on_nwfilter_binding(
    binding: NwFilterBindingRef, procedure: str, **arguments: object
) -> Operation[object]:
    """Call a procedure on a network filter binding.

    :param binding: the binding.
    :param procedure: the procedure; the binding is its ``nwfilter`` argument.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the daemon's reply.
    """
    lookup = nwfilter_binding_lookup(binding)
    return (yield from on_object(lookup, "nwfilter", procedure, arguments))


def as_bool(reply: object) -> bool:
    """Check that a reply is a yes/no number and make it a ``bool``.

    :param reply: what the daemon sent.
    :returns: ``True`` for a non-zero number.
    :raises TypeError: if it is not a number.
    """
    return bool(as_int(reply))


def as_params(reply: object) -> dict[str, TypedValue]:
    """Check that a reply is a dict of typed parameters.

    :param reply: what the daemon sent.
    :returns: the parameters.
    :raises TypeError: if it is not a dict.
    """
    if not isinstance(reply, dict):
        raise TypeError(f"expected typed parameters, got {reply!r}")
    return reply


def as_struct[StructT](reply: object, struct_type: type[StructT]) -> StructT:
    """Check that a reply is a given wire struct.

    :param reply: what the daemon sent.
    :param struct_type: the generated return struct class.
    :returns: the struct.
    :raises TypeError: if it is something else.
    """
    if not isinstance(reply, struct_type):
        raise TypeError(f"expected {struct_type.__name__}, got {reply!r}")
    return reply


def as_list(reply: object) -> list[object]:
    """Check that a reply is a list.

    :param reply: what the daemon sent.
    :returns: the items.
    :raises TypeError: if it is not a list.
    """
    if not isinstance(reply, list):
        raise TypeError(f"expected a list, got {reply!r}")
    return reply


def as_bytes(reply: object) -> bytes:
    """Check that a reply is raw bytes.

    :param reply: what the daemon sent.
    :returns: the bytes.
    :raises TypeError: if it is something else.
    """
    if not isinstance(reply, bytes):
        raise TypeError(f"expected bytes, got {reply!r}")
    return reply


def get_typed_parameters(
    domain: DomainRef, procedure: str, flags: int, **arguments: object
) -> Operation[dict[str, TypedValue]]:
    """Read the typed parameters of a domain: the count, then the values.

    :param domain: the domain.
    :param procedure: a ``domain_get_*`` procedure that has ``nparams`` and
        returns ``params``.
    :param flags: the flags of the call.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the parameters by name.
    """
    return (
        yield from read_parameters(
            partial(on_domain, domain), procedure, flags, **arguments
        )
    )


def read_parameters(
    caller: Callable[..., Operation[object]],
    procedure: str,
    flags: int,
    **arguments: object,
) -> Operation[dict[str, TypedValue]]:
    """Read typed parameters with libvirt's two calls: the count, then the values.

    :param caller: calls a procedure on the object, e.g. ``partial(on_domain, d)``.
    :param procedure: a ``*_get_*`` procedure that has ``nparams`` and returns
        ``params``.
    :param flags: the flags of the call.
    :param arguments: the other arguments of the procedure, by name.
    :returns: the parameters by name.
    """
    first = yield from caller(procedure, nparams=0, flags=flags, **arguments)
    count = parameter_count(first)

    reply = yield from caller(procedure, nparams=count, flags=flags, **arguments)
    return typed_params.from_wire(parameters_of(reply))


def parameter_count(reply: object) -> int:
    """Read ``nparams`` from the reply to a count request.

    :param reply: a return struct that has an ``nparams`` field.
    :returns: the number of parameters.
    :raises TypeError: if the reply has none.
    """
    count = getattr(reply, "nparams", None)
    if not isinstance(count, int):
        raise TypeError(f"expected a reply with nparams, got {reply!r}")
    return count


def parameters_of(reply: object) -> list[TypedParam]:
    """Read ``params`` from a reply of several fields.

    :param reply: a return struct that has a ``params`` field.
    :returns: the typed parameters.
    :raises TypeError: if the reply has none.
    """
    parameters = getattr(reply, "params", None)
    if not isinstance(parameters, list):
        raise TypeError(f"expected a reply with params, got {reply!r}")
    return parameters


def as_handle(operation: Operation[object]) -> Operation[Handle]:
    """Run an operation and check that it gave an object handle.

    :param operation: an operation whose result is an object handle.
    :returns: the handle.
    :raises TypeError: if it is something else.
    """
    reply = yield from operation
    if not isinstance(reply, Handle):
        raise TypeError(f"expected a Handle, got {reply!r}")
    return reply
