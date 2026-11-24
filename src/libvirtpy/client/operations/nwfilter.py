"""Operations on network filters."""

from libvirtpy.client.operations._common import (
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    one_handle,
)
from libvirtpy.client.references import (
    NwFilterRef,
    nwfilter_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.nwfilter import Filter

__all__ = [
    "define_nwfilter",
    "list_nwfilters",
    "lookup_nwfilter",
    "undefine_nwfilter",
]


def lookup_nwfilter(nwfilter: NwFilterRef) -> Operation[Filter]:
    """Return a network filter.

    :param nwfilter: a name, UUID or ``Filter`` model.
    :returns: the filter.
    :raises NoFilterError: if there is no such filter.
    """
    handle = yield from one_handle(nwfilter_lookup(nwfilter))
    return (yield from fetch_model("nwfilter_get_xml_desc", handle, Filter))


def list_nwfilters() -> Operation[list[Filter]]:
    """Return the network filters.

    :returns: the filters.
    """
    handles = yield from many_handles(
        Request("connect_list_all_nwfilters", {"need_results": 1, "flags": 0})
    )
    return (yield from fetch_models("nwfilter_get_xml_desc", handles, Filter))


def define_nwfilter(nwfilter: Filter | str, *, flags: int = 0) -> Operation[Filter]:
    """Define (or redefine) a network filter.

    :param nwfilter: the filter, as a model or XML text.
    :param flags: ``virNWFilterDefineFlags``.
    :returns: the stored filter.
    """
    xml = as_xml(nwfilter)
    handle = yield from one_handle(
        Request("nwfilter_define_xml_flags", {"xml": xml, "flags": flags})
    )
    return (yield from fetch_model("nwfilter_get_xml_desc", handle, Filter))


def undefine_nwfilter(nwfilter: NwFilterRef) -> Operation[None]:
    """Remove a network filter.

    :param nwfilter: the filter.
    """
    handle = yield from one_handle(nwfilter_lookup(nwfilter))
    yield Request("nwfilter_undefine", {"nwfilter": handle})
