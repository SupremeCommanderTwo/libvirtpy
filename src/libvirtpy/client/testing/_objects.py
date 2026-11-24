"""Connection data, networks, secrets, filters, interfaces and host devices."""

from libvirtpy.client.testing._common import (
    _CAPABILITIES,
    _DOMAIN_CAPABILITIES,
    _POOL_CAPABILITIES,
    _SYSINFO,
    Action,
    Arguments,
    _handle_argument,
    _handle_of,
    _text,
    _xml_of,
)
from libvirtpy.client.testing._state import FakeState
from libvirtpy.client.transport import Handle
from libvirtpy.rpc.errors import (
    ErrorNumber,
    OperationInvalidError,
)
from libvirtpy.xml.interface import HostInterface
from libvirtpy.xml.network import Network
from libvirtpy.xml.nodedev import Device
from libvirtpy.xml.nwfilter import Filter
from libvirtpy.xml.secret import Secret


class ObjectActions(FakeState):
    """Connection data, networks, secrets, filters, interfaces and host devices."""

    def _connection_actions(self) -> dict[str, Action]:
        return {
            "connect_get_version": lambda _: 11006000,
            "connect_get_hostname": lambda _: "fake-host",
            "connect_get_capabilities": lambda _: _CAPABILITIES,
            "connect_get_domain_capabilities": lambda _: _DOMAIN_CAPABILITIES,
            "connect_get_storage_pool_capabilities": lambda _: _POOL_CAPABILITIES,
            "connect_get_sysinfo": lambda _: _SYSINFO,
        }

    def _network_actions(self) -> dict[str, Action]:
        return {
            "connect_list_all_networks": lambda a: self._list(self._networks, a, True),
            "network_lookup_by_name": lambda a: self._find_by_name(
                self._networks, _text(a, "name"), self._no_network
            ),
            "network_lookup_by_uuid": lambda a: self._find_by_uuid(
                self._networks, _text(a, "uuid"), self._no_network
            ),
            "network_get_xml_desc": lambda a: _xml_of(
                self._get(self._networks, a, self._no_network).model
            ),
            "network_define_xml_flags": lambda a: self._define(
                self._networks, Network, _text(a, "xml")
            ),
            "network_create_xml_flags": lambda a: self._create_transient(
                self._networks, Network, _text(a, "xml")
            ),
            "network_undefine": lambda a: self._undefine(
                self._networks, a, self._no_network
            ),
            "network_create": lambda a: self._start(
                self._networks, a, self._no_network
            ),
            "network_destroy": lambda a: self._stop(
                self._networks, a, self._no_network
            ),
            "network_get_autostart": lambda a: int(
                self._get(self._networks, a, self._no_network).autostart
            ),
            "network_set_autostart": lambda a: self._set_autostart(
                self._networks, a, self._no_network
            ),
        }

    def _secret_actions(self) -> dict[str, Action]:
        return {
            "connect_list_all_secrets": lambda _: [
                _handle_of(e.model) for e in self._secrets.values()
            ],
            "secret_lookup_by_uuid": lambda a: self._find_by_uuid(
                self._secrets, _text(a, "uuid"), self._no_secret
            ),
            "secret_get_xml_desc": lambda a: _xml_of(
                self._get(self._secrets, a, self._no_secret).model
            ),
            "secret_define_xml": lambda a: self._define(
                self._secrets, Secret, _text(a, "xml")
            ),
            "secret_undefine": lambda a: self._undefine(
                self._secrets, a, self._no_secret, check_active=False
            ),
            "secret_set_value": self._set_secret_value,
            "secret_get_value": self._get_secret_value,
        }

    def _filter_actions(self) -> dict[str, Action]:
        return {
            "connect_list_all_nwfilters": lambda _: [
                _handle_of(e.model) for e in self._filters.values()
            ],
            "nwfilter_lookup_by_name": lambda a: self._find_by_name(
                self._filters, _text(a, "name"), self._no_filter
            ),
            "nwfilter_lookup_by_uuid": lambda a: self._find_by_uuid(
                self._filters, _text(a, "uuid"), self._no_filter
            ),
            "nwfilter_get_xml_desc": lambda a: _xml_of(
                self._get(self._filters, a, self._no_filter).model
            ),
            "nwfilter_define_xml_flags": lambda a: self._define(
                self._filters, Filter, _text(a, "xml")
            ),
            "nwfilter_undefine": lambda a: self._undefine(
                self._filters, a, self._no_filter, check_active=False
            ),
        }

    def _interface_actions(self) -> dict[str, Action]:
        return {
            "connect_list_all_interfaces": lambda a: self._list(
                self._interfaces, a, True
            ),
            "interface_lookup_by_name": lambda a: self._find_by_name(
                self._interfaces, _text(a, "name"), self._no_interface
            ),
            "interface_lookup_by_mac_string": self._lookup_interface_by_mac,
            "interface_get_xml_desc": lambda a: _xml_of(
                self._get(self._interfaces, a, self._no_interface).model
            ),
            "interface_define_xml": lambda a: self._define(
                self._interfaces, HostInterface, _text(a, "xml")
            ),
            "interface_undefine": lambda a: self._undefine(
                self._interfaces, a, self._no_interface
            ),
            "interface_create": lambda a: self._start(
                self._interfaces, a, self._no_interface
            ),
            "interface_destroy": lambda a: self._stop(
                self._interfaces, a, self._no_interface
            ),
        }

    def _device_actions(self) -> dict[str, Action]:
        return {
            "connect_list_all_node_devices": self._list_devices,
            "node_device_lookup_by_name": self._lookup_device,
            "node_device_get_xml_desc": lambda a: _xml_of(self._device(a)),
            "node_device_create_xml": self._create_device,
            "node_device_destroy": self._destroy_device,
        }

    def _set_secret_value(self, arguments: Arguments) -> None:
        entry = self._get(self._secrets, arguments, self._no_secret)
        value = arguments["value"]
        if not isinstance(value, bytes):
            raise TypeError("a secret value is bytes")
        entry.secret_value = value

    def _get_secret_value(self, arguments: Arguments) -> bytes:
        entry = self._get(self._secrets, arguments, self._no_secret)
        if entry.model.private:
            raise OperationInvalidError(
                "the secret is private", code=ErrorNumber.OPERATION_INVALID
            )
        if entry.secret_value is None:
            raise OperationInvalidError(
                "the secret has no value", code=ErrorNumber.OPERATION_INVALID
            )
        return entry.secret_value

    def _lookup_interface_by_mac(self, arguments: Arguments) -> Handle:
        wanted = _text(arguments, "mac").lower()
        for entry in self._interfaces.values():
            if entry.model.mac and entry.model.mac.address.lower() == wanted:
                return _handle_of(entry.model)
        raise self._no_interface(wanted)

    def _device(self, arguments: Arguments) -> Device:
        handle = _handle_argument(arguments)
        device = self._devices.get(handle.name)
        if device is None:
            raise self._no_device(handle.name)
        return device

    def _list_devices(self, _arguments: Arguments) -> list[Handle]:
        return [Handle(name=name) for name in self._devices]

    def _lookup_device(self, arguments: Arguments) -> Handle:
        name = _text(arguments, "name")
        if name not in self._devices:
            raise self._no_device(name)
        return Handle(name=name)

    def _create_device(self, arguments: Arguments) -> Handle:
        device = Device.from_xml(_text(arguments, "xml_desc"))
        self._devices[device.name] = device
        return Handle(name=device.name)

    def _destroy_device(self, arguments: Arguments) -> None:
        name = _text(arguments, "name")
        if name not in self._devices:
            raise self._no_device(name)
        del self._devices[name]
