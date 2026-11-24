"""Operations on network filter bindings (a filter attached to a port device)."""

from libvirtpy.client.operations._common import (
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    on_nwfilter_binding,
    one_handle,
)
from libvirtpy.client.references import NwFilterBindingRef, nwfilter_binding_lookup
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.nwfilter import FilterBinding

__all__ = [
    "create_nwfilter_binding",
    "delete_nwfilter_binding",
    "list_nwfilter_bindings",
    "lookup_nwfilter_binding",
]


def list_nwfilter_bindings(*, flags: int = 0) -> Operation[list[FilterBinding]]:
    """Return the network filter bindings of the host.

    :param flags: reserved, 0.
    :returns: the bindings.
    """
    handles = yield from many_handles(
        Request(
            "connect_list_all_nwfilter_bindings", {"need_results": 1, "flags": flags}
        )
    )
    return (
        yield from fetch_models("nwfilter_binding_get_xml_desc", handles, FilterBinding)
    )


def lookup_nwfilter_binding(binding: NwFilterBindingRef) -> Operation[FilterBinding]:
    """Return the binding of a port device.

    :param binding: the name of the port device (``vnet0``), or a ``FilterBinding``.
    :returns: the binding.
    :raises NoFilterBindingError: if there is none.
    """
    found = yield from one_handle(nwfilter_binding_lookup(binding))
    return (
        yield from fetch_model("nwfilter_binding_get_xml_desc", found, FilterBinding)
    )


def create_nwfilter_binding(
    binding: FilterBinding | str, *, flags: int = 0
) -> Operation[FilterBinding]:
    """Attach a network filter to a port device.

    :param binding: the binding description, as a model or XML.
    :param flags: reserved, 0.
    :returns: the binding as the daemon created it.
    """
    created = yield from one_handle(
        Request("nwfilter_binding_create_xml", {"xml": as_xml(binding), "flags": flags})
    )
    return (
        yield from fetch_model("nwfilter_binding_get_xml_desc", created, FilterBinding)
    )


def delete_nwfilter_binding(binding: NwFilterBindingRef) -> Operation[None]:
    """Remove the network filter of a port device.

    :param binding: the name of the port device, or a ``FilterBinding``.
    """
    yield from on_nwfilter_binding(binding, "nwfilter_binding_delete")
