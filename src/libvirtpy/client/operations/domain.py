"""Operations on domains (virtual machines): lifecycle, state, devices."""

from libvirtpy.client.operations._common import (
    DOMAINS_ACTIVE,
    DOMAINS_INACTIVE,
    as_int,
    as_xml,
    fetch_model,
    fetch_models,
    many_handles,
    one_handle,
)
from libvirtpy.client.references import (
    DomainRef,
    domain_lookup,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.client.types import DomainInfo, DomainState
from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml.domain import Domain

__all__ = [
    "attach_domain_device",
    "create_domain",
    "define_domain",
    "destroy_domain",
    "detach_domain_device",
    "get_domain_autostart",
    "get_domain_info",
    "get_domain_state",
    "list_domains",
    "lookup_domain",
    "reboot_domain",
    "reset_domain",
    "resume_domain",
    "set_domain_autostart",
    "set_domain_memory",
    "set_domain_vcpus",
    "shutdown_domain",
    "start_domain",
    "suspend_domain",
    "undefine_domain",
    "update_domain_device",
]


def lookup_domain(domain: DomainRef) -> Operation[Domain]:
    """Return the configuration of a domain.

    :param domain: a runtime id, name, UUID or ``Domain`` model.
    :returns: the domain, with the live state (``id``) if it is running.
    :raises NoDomainError: if there is no such domain.
    """
    handle = yield from one_handle(domain_lookup(domain))
    return (yield from fetch_model("domain_get_xml_desc", handle, Domain))


def list_domains(*, active: bool | None = None) -> Operation[list[Domain]]:
    """Return the domains, one request per domain for its XML.

    :param active: ``True`` for running domains only, ``False`` for the others,
        ``None`` for all.
    :returns: the domains.
    """
    flags = {True: DOMAINS_ACTIVE, False: DOMAINS_INACTIVE, None: 0}[active]
    handles = yield from many_handles(
        Request("connect_list_all_domains", {"need_results": 1, "flags": flags})
    )
    return (yield from fetch_models("domain_get_xml_desc", handles, Domain))


def define_domain(domain: Domain | str, *, flags: int = 0) -> Operation[Domain]:
    """Define (or redefine) a persistent domain without starting it.

    :param domain: the configuration, as a model or XML text.
    :param flags: ``virDomainDefineFlags``.
    :returns: the stored configuration, with what libvirt filled in (UUID, ...).
    """
    xml = as_xml(domain)
    handle = yield from one_handle(
        Request("domain_define_xml_flags", {"xml": xml, "flags": flags})
    )
    return (yield from fetch_model("domain_get_xml_desc", handle, Domain))


def create_domain(domain: Domain | str, *, flags: int = 0) -> Operation[Domain]:
    """Start a transient domain: it disappears when it stops.

    :param domain: the configuration, as a model or XML text.
    :param flags: ``virDomainCreateFlags``.
    :returns: the running domain.
    """
    xml = as_xml(domain)
    handle = yield from one_handle(
        Request("domain_create_xml", {"xml_desc": xml, "flags": flags})
    )
    return (yield from fetch_model("domain_get_xml_desc", handle, Domain))


def undefine_domain(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Remove a persistent domain's definition.

    :param domain: the domain.
    :param flags: ``virDomainUndefineFlagsValues``.
    :raises OperationInvalidError: if the domain is running.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request("domain_undefine_flags", {"dom": handle, "flags": flags})


def start_domain(domain: DomainRef, *, flags: int = 0) -> Operation[Domain]:
    """Start a defined domain.

    :param domain: the domain.
    :param flags: ``virDomainCreateFlags``, e.g. start paused.
    :returns: the domain, now running (it has an ``id``).
    :raises OperationInvalidError: if the domain is already running.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request("domain_create_with_flags", {"dom": handle, "flags": flags})
    return (yield from fetch_model("domain_get_xml_desc", handle, Domain))


def shutdown_domain(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Ask the guest to shut down cleanly.

    :param domain: the domain.
    :param flags: ``virDomainShutdownFlagValues``: how to ask (ACPI, guest
        agent...).
    :raises OperationInvalidError: if the domain is not running.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request("domain_shutdown_flags", {"dom": handle, "flags": flags})


def destroy_domain(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Stop a domain at once, like pulling the power.

    :param domain: the domain.
    :param flags: ``virDomainDestroyFlagsValues``.
    :raises OperationInvalidError: if the domain is not running.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request("domain_destroy_flags", {"dom": handle, "flags": flags})


def reboot_domain(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Ask the guest to reboot.

    :param domain: the domain.
    :param flags: ``virDomainShutdownFlagValues``.
    :raises OperationInvalidError: if the domain is not running.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request("domain_reboot", {"dom": handle, "flags": flags})


def suspend_domain(domain: DomainRef) -> Operation[None]:
    """Pause a running domain.

    :param domain: the domain.
    :raises OperationInvalidError: if the domain is not running.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request("domain_suspend", {"dom": handle})


def resume_domain(domain: DomainRef) -> Operation[None]:
    """Resume a paused domain.

    :param domain: the domain.
    :raises OperationInvalidError: if the domain is not paused.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request("domain_resume", {"dom": handle})


def reset_domain(domain: DomainRef) -> Operation[None]:
    """Reset a running domain, like pressing the reset button.

    :param domain: the domain.
    :raises OperationInvalidError: if the domain is not running.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request("domain_reset", {"dom": handle, "flags": 0})


def get_domain_state(domain: DomainRef) -> Operation[DomainState]:
    """Return the run state of a domain.

    :param domain: the domain.
    :returns: the state.
    """
    handle = yield from one_handle(domain_lookup(domain))
    return DomainState(
        as_int((yield Request("domain_get_state", {"dom": handle, "flags": 0})))
    )


def get_domain_info(domain: DomainRef) -> Operation[DomainInfo]:
    """Return the run time numbers of a domain.

    :param domain: the domain.
    :returns: state, memory, vCPU count and CPU time.
    """
    handle = yield from one_handle(domain_lookup(domain))
    reply = yield Request("domain_get_info", {"dom": handle})
    if not isinstance(reply, DomainInfo):
        raise TypeError(f"expected DomainInfo, got {reply!r}")
    return reply


def set_domain_vcpus(
    domain: DomainRef, count: int, *, flags: int = 0
) -> Operation[Domain]:
    """Change the number of virtual CPUs.

    :param domain: the domain.
    :param count: the new number of vCPUs.
    :param flags: ``virDomainVcpuFlags``: live, config, maximum.
    :returns: the domain with the new setting.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request(
        "domain_set_vcpus_flags", {"dom": handle, "nvcpus": count, "flags": flags}
    )
    return (yield from fetch_model("domain_get_xml_desc", handle, Domain))


def set_domain_memory(
    domain: DomainRef, kib: int, *, flags: int = 0
) -> Operation[Domain]:
    """Change the memory of a domain.

    :param domain: the domain.
    :param kib: the new amount, in KiB.
    :param flags: ``virDomainMemoryModFlags``: live, config, maximum.
    :returns: the domain with the new setting.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request(
        "domain_set_memory_flags", {"dom": handle, "memory": kib, "flags": flags}
    )
    return (yield from fetch_model("domain_get_xml_desc", handle, Domain))


def get_domain_autostart(domain: DomainRef) -> Operation[bool]:
    """Tell whether a domain starts with the host.

    :param domain: the domain.
    :returns: ``True`` if it starts at boot.
    """
    handle = yield from one_handle(domain_lookup(domain))
    return bool(as_int((yield Request("domain_get_autostart", {"dom": handle}))))


def set_domain_autostart(domain: DomainRef, enabled: bool) -> Operation[None]:
    """Make a domain start (or not) with the host.

    :param domain: the domain.
    :param enabled: ``True`` to start it at boot.
    """
    handle = yield from one_handle(domain_lookup(domain))
    yield Request("domain_set_autostart", {"dom": handle, "autostart": int(enabled)})


def attach_domain_device(
    domain: DomainRef, device: LibvirtXmlModel | str, *, flags: int = 0
) -> Operation[None]:
    """Plug a device into a domain.

    :param domain: the domain.
    :param device: the device, as a model (``Disk``, ``Interface``, ...) or XML.
    :param flags: ``virDomainDeviceModifyFlags``: live, config.
    """
    handle = yield from one_handle(domain_lookup(domain))
    arguments = {"dom": handle, "xml": as_xml(device), "flags": flags}
    yield Request("domain_attach_device_flags", arguments)


def detach_domain_device(
    domain: DomainRef, device: LibvirtXmlModel | str, *, flags: int = 0
) -> Operation[None]:
    """Unplug a device from a domain.

    :param domain: the domain.
    :param device: the device, as a model or XML.
    :param flags: ``virDomainDeviceModifyFlags``: live, config.
    """
    handle = yield from one_handle(domain_lookup(domain))
    arguments = {"dom": handle, "xml": as_xml(device), "flags": flags}
    yield Request("domain_detach_device_flags", arguments)


def update_domain_device(
    domain: DomainRef, device: LibvirtXmlModel | str, *, flags: int = 0
) -> Operation[None]:
    """Change a device of a domain.

    :param domain: the domain.
    :param device: the new device configuration, as a model or XML.
    :param flags: ``virDomainDeviceModifyFlags``: live, config.
    """
    handle = yield from one_handle(domain_lookup(domain))
    arguments = {"dom": handle, "xml": as_xml(device), "flags": flags}
    yield Request("domain_update_device_flags", arguments)
