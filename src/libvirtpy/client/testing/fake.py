"""The fake daemon: dispatch of requests to the actions of each area."""

from libvirtpy.client.testing._common import (
    _PCI_DEVICE,
    Action,
    _check_against_protocol,
    _Entry,
)
from libvirtpy.client.testing._domains import DomainActions
from libvirtpy.client.testing._objects import ObjectActions
from libvirtpy.client.testing._storage import StorageActions
from libvirtpy.client.transport import Request
from libvirtpy.rpc.errors import (
    ErrorNumber,
    NotSupportedError,
)
from libvirtpy.xml.domain import Domain
from libvirtpy.xml.interface import HostInterface
from libvirtpy.xml.network import Network
from libvirtpy.xml.nodedev import Device
from libvirtpy.xml.nwfilter import Filter
from libvirtpy.xml.secret import Secret
from libvirtpy.xml.snapshot import Snapshot
from libvirtpy.xml.storage import Pool, Volume


class FakeLibvirt(DomainActions, StorageActions, ObjectActions):
    """The fake daemon; also the sync ``Transport`` of a ``LibvirtClient``."""

    def __init__(self) -> None:
        """Create a daemon with no domains and one host device."""
        self._next_domain_id = 1
        self._domains: dict[str, _Entry[Domain]] = {}
        self._networks: dict[str, _Entry[Network]] = {}
        self._pools: dict[str, _Entry[Pool]] = {}
        self._volumes: dict[tuple[str, str], Volume] = {}
        self._secrets: dict[str, _Entry[Secret]] = {}
        self._filters: dict[str, _Entry[Filter]] = {}
        self._interfaces: dict[str, _Entry[HostInterface]] = {}
        self._devices: dict[str, Device] = {}
        self._snapshots: dict[tuple[str, str], Snapshot] = {}
        self._snapshot_count = 0
        self.requests: list[Request] = []
        """Every request served, in order: handy to see what a client sent."""
        self._actions = self._build_actions()
        device = Device.from_xml(_PCI_DEVICE)
        self._devices[device.name] = device

    def call(self, request: Request) -> object:
        """Serve one request.

        :param request: the call to make.
        :returns: the reply.
        :raises LibvirtError: for the errors a real daemon would report.
        """
        self.requests.append(request)
        _check_against_protocol(request)
        action = self._actions.get(request.procedure)
        if action is None:
            raise NotSupportedError(
                f"the fake daemon does not know {request.procedure}",
                code=ErrorNumber.NO_SUPPORT,
            )
        return action(request.arguments)

    def close(self) -> None:
        """Close the connection (nothing to do for the fake)."""

    def _build_actions(self) -> dict[str, Action]:
        return {
            **self._connection_actions(),
            **self._domain_actions(),
            **self._snapshot_actions(),
            **self._network_actions(),
            **self._pool_actions(),
            **self._volume_actions(),
            **self._secret_actions(),
            **self._filter_actions(),
            **self._interface_actions(),
            **self._device_actions(),
        }
