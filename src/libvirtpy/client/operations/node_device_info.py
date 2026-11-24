"""Operations on host devices beyond listing and creating them."""

from libvirtpy.client.operations._common import (
    as_bool,
    as_list,
    as_text,
    as_xml,
    fetch_model,
    on_node_device,
    one_handle,
)
from libvirtpy.client.references import NodeDeviceRef
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.nodedev import Device

__all__ = [
    "define_node_device",
    "detach_node_device",
    "get_node_device_autostart",
    "get_node_device_parent",
    "is_node_device_active",
    "is_node_device_persistent",
    "list_node_device_capabilities",
    "lookup_node_device_scsi_host_by_wwn",
    "reattach_node_device",
    "reset_node_device",
    "set_node_device_autostart",
    "start_node_device",
    "undefine_node_device",
    "update_node_device",
]


def get_node_device_parent(device: NodeDeviceRef) -> Operation[str | None]:
    """Return the name of the parent of a host device.

    :param device: the device.
    :returns: the parent's name, or ``None`` if it has none.
    """
    reply = yield from on_node_device(device, "node_device_get_parent")
    return None if reply is None else as_text(reply)


def list_node_device_capabilities(
    device: NodeDeviceRef, *, max_names: int = 256
) -> Operation[list[str]]:
    """List the capabilities of a host device.

    :param device: the device.
    :param max_names: how many names to ask for at most.
    :returns: the capability names, e.g. ``pci``, ``net``.
    """
    reply = yield from on_node_device(
        device, "node_device_list_caps", maxnames=max_names
    )
    return [as_text(name) for name in as_list(reply)]


def detach_node_device(
    device: NodeDeviceRef, driver: str | None = None, *, flags: int = 0
) -> Operation[None]:
    """Detach a device from its host driver, to give it to a guest.

    :param device: the device.
    :param driver: the driver to bind it to (``vfio``); ``None`` for the default.
    :param flags: reserved, 0.
    """
    yield from on_node_device(
        device, "node_device_detach_flags", driver_name=driver, flags=flags
    )


def reattach_node_device(device: NodeDeviceRef) -> Operation[None]:
    """Give a device back to its host driver.

    :param device: the device.
    """
    yield from on_node_device(device, "node_device_re_attach")


def reset_node_device(device: NodeDeviceRef) -> Operation[None]:
    """Reset a host device.

    :param device: the device.
    """
    yield from on_node_device(device, "node_device_reset")


def lookup_node_device_scsi_host_by_wwn(
    wwnn: str, wwpn: str, *, flags: int = 0
) -> Operation[Device]:
    """Find a SCSI host device by its world wide names.

    :param wwnn: the world wide node name.
    :param wwpn: the world wide port name.
    :param flags: reserved, 0.
    :returns: the device.
    :raises NoNodeDeviceError: if there is none.
    """
    found = yield from one_handle(
        Request(
            "node_device_lookup_scsi_host_by_wwn",
            {"wwnn": wwnn, "wwpn": wwpn, "flags": flags},
        )
    )
    return (yield from fetch_model("node_device_get_xml_desc", found, Device))


def define_node_device(device: Device | str, *, flags: int = 0) -> Operation[Device]:
    """Define a persistent mediated device (stored, not yet started).

    :param device: the device description, as a model or XML.
    :param flags: reserved, 0.
    :returns: the device as the daemon stored it.
    """
    created = yield from one_handle(
        Request("node_device_define_xml", {"xml_desc": as_xml(device), "flags": flags})
    )
    return (yield from fetch_model("node_device_get_xml_desc", created, Device))


def undefine_node_device(device: NodeDeviceRef, *, flags: int = 0) -> Operation[None]:
    """Remove the stored definition of a mediated device.

    :param device: the device.
    :param flags: reserved, 0.
    """
    yield from on_node_device(device, "node_device_undefine", flags=flags)


def start_node_device(device: NodeDeviceRef, *, flags: int = 0) -> Operation[None]:
    """Start a defined mediated device.

    :param device: the device.
    :param flags: reserved, 0.
    """
    yield from on_node_device(device, "node_device_create", flags=flags)


def get_node_device_autostart(device: NodeDeviceRef) -> Operation[bool]:
    """Tell whether a mediated device starts at host boot.

    :param device: the device.
    :returns: ``True`` if it does.
    """
    return as_bool((yield from on_node_device(device, "node_device_get_autostart")))


def set_node_device_autostart(device: NodeDeviceRef, enabled: bool) -> Operation[None]:
    """Choose whether a mediated device starts at host boot.

    :param device: the device.
    :param enabled: ``True`` to start it at boot.
    """
    yield from on_node_device(
        device, "node_device_set_autostart", autostart=int(enabled)
    )


def is_node_device_active(device: NodeDeviceRef) -> Operation[bool]:
    """Tell whether a mediated device is started.

    :param device: the device.
    :returns: ``True`` if it is active.
    """
    return as_bool((yield from on_node_device(device, "node_device_is_active")))


def is_node_device_persistent(device: NodeDeviceRef) -> Operation[bool]:
    """Tell whether a mediated device has a stored definition.

    :param device: the device.
    :returns: ``True`` if persistent.
    """
    return as_bool((yield from on_node_device(device, "node_device_is_persistent")))


def update_node_device(
    device: NodeDeviceRef, definition: Device | str, *, flags: int = 0
) -> Operation[None]:
    """Change the definition of a mediated device.

    :param device: the device.
    :param definition: the new description, as a model or XML.
    :param flags: ``virNodeDeviceUpdateFlags``: 1 affect the running device.
    """
    yield from on_node_device(
        device, "node_device_update", xml_desc=as_xml(definition), flags=flags
    )
