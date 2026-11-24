"""Domains and their snapshots."""

import time

from libvirtpy.client.testing._common import (
    _SNAPSHOT_STATES,
    _START_PAUSED,
    Action,
    Arguments,
    _device_identity,
    _Entry,
    _handle_argument,
    _handle_of,
    _int,
    _key_of,
    _text,
    _xml_of,
)
from libvirtpy.client.testing._state import FakeState
from libvirtpy.client.transport import Handle
from libvirtpy.client.types import DomainInfo, DomainState
from libvirtpy.rpc.errors import (
    ErrorNumber,
    ExistsError,
    LibvirtError,
    OperationInvalidError,
)
from libvirtpy.xml.domain import CurrentMemory, Domain, Vcpu
from libvirtpy.xml.domain.devices import Devices
from libvirtpy.xml.snapshot import Snapshot, SnapshotParent


class DomainActions(FakeState):
    """Domains and their snapshots."""

    def _domain_actions(self) -> dict[str, Action]:
        return {
            "connect_list_all_domains": self._list_domains,
            "domain_lookup_by_id": self._lookup_domain_by_id,
            "domain_lookup_by_name": lambda a: self._find_by_name(
                self._domains, _text(a, "name"), self._no_domain
            ),
            "domain_lookup_by_uuid": lambda a: self._find_by_uuid(
                self._domains, _text(a, "uuid"), self._no_domain
            ),
            "domain_get_xml_desc": lambda a: _xml_of(self._domain(a).model),
            "domain_define_xml_flags": self._define_domain,
            "domain_create_xml": self._create_domain,
            "domain_create_with_flags": self._start_domain,
            "domain_undefine_flags": self._undefine_domain,
            "domain_shutdown_flags": self._shutdown_domain,
            "domain_destroy_flags": self._destroy_domain,
            "domain_reboot": self._require_running,
            "domain_reset": self._require_running,
            "domain_suspend": self._suspend_domain,
            "domain_resume": self._resume_domain,
            "domain_get_state": lambda a: int(self._domain(a).state),
            "domain_get_info": self._domain_info,
            "domain_set_vcpus_flags": self._set_vcpus,
            "domain_set_memory_flags": self._set_memory,
            "domain_get_autostart": lambda a: int(self._domain(a).autostart),
            "domain_set_autostart": self._set_domain_autostart,
            "domain_attach_device_flags": self._attach_device,
            "domain_detach_device_flags": self._detach_device,
            "domain_update_device_flags": self._update_device,
        }

    def _snapshot_actions(self) -> dict[str, Action]:
        return {
            "domain_list_all_snapshots": self._list_snapshots,
            "domain_snapshot_lookup_by_name": self._lookup_snapshot,
            "domain_snapshot_create_xml": self._create_snapshot,
            "domain_snapshot_get_xml_desc": lambda a: _xml_of(self._snapshot(a)),
            "domain_revert_to_snapshot": self._revert_snapshot,
            "domain_snapshot_delete": self._delete_snapshot,
        }

    def _domain(self, arguments: Arguments) -> _Entry[Domain]:
        return self._get(self._domains, arguments, self._no_domain)

    def _list_domains(self, arguments: Arguments) -> list[Handle]:
        return self._list(self._domains, arguments, inactive_is_one=False)

    def _lookup_domain_by_id(self, arguments: Arguments) -> Handle:
        wanted = _int(arguments, "id")
        for entry in self._domains.values():
            if entry.model.id == wanted:
                return _handle_of(entry.model)
        raise self._no_domain(str(wanted))

    def _define_domain(self, arguments: Arguments) -> Handle:
        return self._define(self._domains, Domain, _text(arguments, "xml"))

    def _create_domain(self, arguments: Arguments) -> Handle:
        handle = self._create_transient(
            self._domains, Domain, _text(arguments, "xml_desc")
        )
        entry = self._domains[handle.name]
        self._run(entry, paused=bool(_int(arguments, "flags") & _START_PAUSED))
        return _handle_of(entry.model)

    def _start_domain(self, arguments: Arguments) -> None:
        entry = self._domain(arguments)
        if entry.state != DomainState.SHUTOFF:
            raise OperationInvalidError(
                f"domain is already {entry.state.name.lower()}",
                code=ErrorNumber.OPERATION_INVALID,
            )
        self._run(entry, paused=bool(_int(arguments, "flags") & _START_PAUSED))

    def _run(self, entry: _Entry[Domain], *, paused: bool) -> None:
        entry.active = True
        entry.state = DomainState.PAUSED if paused else DomainState.RUNNING
        entry.model.id = self._next_domain_id
        self._next_domain_id += 1

    def _stop_domain(self, entry: _Entry[Domain]) -> None:
        entry.active = False
        entry.state = DomainState.SHUTOFF
        entry.model.id = None
        if entry.transient:
            del self._domains[_key_of(entry.model)]

    def _undefine_domain(self, arguments: Arguments) -> None:
        entry = self._domain(arguments)
        if entry.active:
            raise OperationInvalidError(
                "cannot undefine a running domain", code=ErrorNumber.OPERATION_INVALID
            )
        name = entry.model.name
        del self._domains[_key_of(entry.model)]
        for key in [k for k in self._snapshots if k[0] == name]:
            del self._snapshots[key]

    def _shutdown_domain(self, arguments: Arguments) -> None:
        self._stop_domain(self._require_running(arguments))

    def _destroy_domain(self, arguments: Arguments) -> None:
        entry = self._domain(arguments)
        if not entry.active:
            raise OperationInvalidError(
                "domain is not running", code=ErrorNumber.OPERATION_INVALID
            )
        self._stop_domain(entry)

    def _require_running(self, arguments: Arguments) -> _Entry[Domain]:
        entry = self._domain(arguments)
        if not entry.active:
            raise OperationInvalidError(
                "domain is not running", code=ErrorNumber.OPERATION_INVALID
            )
        return entry

    def _suspend_domain(self, arguments: Arguments) -> None:
        entry = self._require_running(arguments)
        if entry.state != DomainState.RUNNING:
            raise OperationInvalidError(
                "domain is already paused", code=ErrorNumber.OPERATION_INVALID
            )
        entry.state = DomainState.PAUSED

    def _resume_domain(self, arguments: Arguments) -> None:
        entry = self._domain(arguments)
        if entry.state != DomainState.PAUSED:
            raise OperationInvalidError(
                "domain is not paused", code=ErrorNumber.OPERATION_INVALID
            )
        entry.state = DomainState.RUNNING

    def _domain_info(self, arguments: Arguments) -> DomainInfo:
        entry = self._domain(arguments)
        model = entry.model
        max_kib = model.memory.to_bytes() // 1024 if model.memory else 0
        kib = (
            model.current_memory.to_bytes() // 1024 if model.current_memory else max_kib
        )
        return DomainInfo(
            state=entry.state,
            max_memory_kib=max_kib,
            memory_kib=kib,
            vcpus=model.vcpu.value if model.vcpu else 1,
            cpu_time_ns=1_000_000 if entry.active else 0,
        )

    def _set_vcpus(self, arguments: Arguments) -> None:
        entry = self._domain(arguments)
        count = _int(arguments, "nvcpus")
        if count < 1:
            raise LibvirtError("invalid vCPU count", code=ErrorNumber.INVALID_ARG)
        entry.model.vcpu = Vcpu(value=count)

    def _set_memory(self, arguments: Arguments) -> None:
        entry = self._domain(arguments)
        entry.model.current_memory = CurrentMemory(
            value=_int(arguments, "memory"), unit="KiB"
        )

    def _set_domain_autostart(self, arguments: Arguments) -> None:
        self._domain(arguments).autostart = bool(_int(arguments, "autostart"))

    def _attach_device(self, arguments: Arguments) -> None:
        entry = self._domain(arguments)
        parsed = Devices.from_xml(f"<devices>{_text(arguments, 'xml')}</devices>")
        devices = entry.model.devices or Devices()
        for name in Devices.model_fields:
            value = getattr(parsed, name)
            if isinstance(value, list):
                setattr(devices, name, [*getattr(devices, name), *value])
            elif value is not None:
                setattr(devices, name, value)
        entry.model.devices = devices

    def _detach_device(self, arguments: Arguments) -> None:
        entry = self._domain(arguments)
        parsed = Devices.from_xml(f"<devices>{_text(arguments, 'xml')}</devices>")
        devices = entry.model.devices or Devices()
        removed = False
        for name in Devices.model_fields:
            wanted = getattr(parsed, name)
            if not isinstance(wanted, list):
                continue
            current = getattr(devices, name)
            kept = [
                d
                for d in current
                if _device_identity(d) not in map(_device_identity, wanted)
            ]
            removed = removed or len(kept) != len(current)
            setattr(devices, name, kept)
        if not removed:
            raise LibvirtError("device not found", code=ErrorNumber.INVALID_ARG)
        entry.model.devices = devices

    def _update_device(self, arguments: Arguments) -> None:
        self._detach_device(arguments)
        self._attach_device(arguments)

    def _snapshot(self, arguments: Arguments) -> Snapshot:
        handle = _handle_argument(arguments)
        snapshot = self._snapshots.get((handle.parent or "", handle.name))
        if snapshot is None:
            raise self._no_snapshot(handle.name)
        return snapshot

    def _list_snapshots(self, arguments: Arguments) -> list[Handle]:
        domain = self._domain(arguments).model.name
        return [
            Handle(name=name, parent=owner)
            for (owner, name) in self._snapshots
            if owner == domain
        ]

    def _lookup_snapshot(self, arguments: Arguments) -> Handle:
        domain = self._domain({"dom": arguments["dom"]}).model.name
        name = _text(arguments, "name")
        if (domain, name) not in self._snapshots:
            raise self._no_snapshot(name)
        return Handle(name=name, parent=domain)

    def _create_snapshot(self, arguments: Arguments) -> Handle:
        entry = self._domain(arguments)
        snapshot = Snapshot.from_xml(_text(arguments, "xml_desc"))
        self._snapshot_count += 1
        domain = entry.model.name
        if snapshot.name is None:
            snapshot.name = f"snapshot{self._snapshot_count}"
        if (domain, snapshot.name) in self._snapshots:
            raise ExistsError(
                f"snapshot {snapshot.name} exists", code=ErrorNumber.DOM_EXIST
            )
        previous = [name for (owner, name) in self._snapshots if owner == domain]
        snapshot.state = _SNAPSHOT_STATES[entry.state]
        snapshot.creation_time = str(int(time.time()) + self._snapshot_count)
        if previous:
            snapshot.parent = SnapshotParent(name=previous[-1])
        self._snapshots[(domain, snapshot.name)] = snapshot
        return Handle(name=snapshot.name, parent=domain)

    def _revert_snapshot(self, arguments: Arguments) -> None:
        handle = _handle_argument(arguments)
        snapshot = self._snapshot(arguments)
        entry = self._domains[handle.parent or ""]
        wanted = next(
            s for s, text in _SNAPSHOT_STATES.items() if text == snapshot.state
        )
        if wanted == DomainState.SHUTOFF and entry.active:
            self._stop_domain(entry)
        elif wanted != DomainState.SHUTOFF and not entry.active:
            self._run(entry, paused=wanted == DomainState.PAUSED)

    def _delete_snapshot(self, arguments: Arguments) -> None:
        handle = _handle_argument(arguments)
        self._snapshot(arguments)
        del self._snapshots[(handle.parent or "", handle.name)]
