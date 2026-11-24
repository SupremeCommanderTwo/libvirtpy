"""Operations on the devices of the host."""

from libvirtpy.client.operations._common import (
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    one_handle,
)
from libvirtpy.client.references import (
    NodeDeviceRef,
    node_device_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.nodedev import Device

__all__ = [
    "create_node_device",
    "destroy_node_device",
    "list_node_devices",
    "lookup_node_device",
]


def lookup_node_device(device: NodeDeviceRef) -> Operation[Device]:
    """Return a device of the host.

    :param device: the device name (``pci_0000_00_1f_2``) or a ``Device`` model.
    :returns: the device and its capabilities.
    :raises NoNodeDeviceError: if there is no such device.
    """
    handle = yield from one_handle(node_device_lookup(device))
    return (yield from fetch_model("node_device_get_xml_desc", handle, Device))


def list_node_devices(*, capability: str | None = None) -> Operation[list[Device]]:
    """Return the devices of the host.

    :param capability: only devices with this capability type (``pci``, ``net``...).
    :returns: the devices.
    """
    arguments = {"need_results": 1, "flags": 0}
    handles = yield from many_handles(
        Request("connect_list_all_node_devices", arguments)
    )
    devices = yield from fetch_models("node_device_get_xml_desc", handles, Device)
    if capability is None:
        return devices
    return [
        device
        for device in devices
        if any(found.type == capability for found in device.capabilities)
    ]


def create_node_device(device: Device | str, *, flags: int = 0) -> Operation[Device]:
    """Create a virtual device on the host (an NPIV vport, a mediated device).

    :param device: the device description, as a model or XML text.
    :param flags: reserved, ``0``.
    :returns: the created device.
    """
    xml = as_xml(device)
    handle = yield from one_handle(
        Request("node_device_create_xml", {"xml_desc": xml, "flags": flags})
    )
    return (yield from fetch_model("node_device_get_xml_desc", handle, Device))


def destroy_node_device(device: NodeDeviceRef) -> Operation[None]:
    """Remove a virtual device created with ``create_node_device``.

    :param device: the device.
    """
    handle = yield from one_handle(node_device_lookup(device))
    yield Request("node_device_destroy", {"name": handle.name})
