"""Operations that change the power or saved state of a domain."""

from libvirtpy.client.operations._common import (
    as_bool,
    as_text,
    as_xml,
    on_domain,
)
from libvirtpy.client.references import DomainRef
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.domain import Domain

__all__ = [
    "define_domain_managed_save_xml",
    "define_saved_domain_xml",
    "dump_domain_core",
    "get_domain_autostart_once",
    "get_domain_managed_save_xml",
    "get_saved_domain_xml",
    "has_domain_managed_save",
    "inject_domain_nmi",
    "reload_domain_graphics",
    "remove_domain_managed_save",
    "rename_domain",
    "restore_domain",
    "save_domain",
    "save_domain_managed",
    "send_domain_keys",
    "send_domain_signal",
    "set_domain_autostart_once",
    "set_domain_lifecycle_action",
    "set_domain_user_password",
    "suspend_domain_for_duration",
    "wake_domain",
]


def suspend_domain_for_duration(
    domain: DomainRef, target: int, duration: int = 0, *, flags: int = 0
) -> Operation[None]:
    """Put the guest to sleep (power management suspend), through the guest agent.

    :param domain: the domain.
    :param target: ``virNodeSuspendTarget``: 0 memory (S3), 1 disk (S4), 2 hybrid.
    :param duration: seconds until the guest wakes up by itself; 0 for no wake-up.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain,
        "domain_pm_suspend_for_duration",
        target=target,
        duration=duration,
        flags=flags,
    )


def wake_domain(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Wake a guest that is suspended by power management.

    :param domain: the domain.
    :param flags: reserved, 0.
    """
    yield from on_domain(domain, "domain_pm_wakeup", flags=flags)


def inject_domain_nmi(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Send a non-maskable interrupt to the guest (often used to trigger a dump).

    :param domain: the domain.
    :param flags: reserved, 0.
    """
    yield from on_domain(domain, "domain_inject_nmi", flags=flags)


def send_domain_keys(
    domain: DomainRef,
    keycodes: list[int],
    *,
    codeset: int = 0,
    holdtime: int = 0,
    flags: int = 0,
) -> Operation[None]:
    """Type keys into the guest, as if pressed together.

    :param domain: the domain.
    :param keycodes: the key codes, in the numbering of ``codeset``.
    :param codeset: ``virKeycodeSet``: 0 Linux, 1 XT, 2 AT set 1, ...
    :param holdtime: how long to hold the keys, in milliseconds.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain,
        "domain_send_key",
        codeset=codeset,
        holdtime=holdtime,
        keycodes=keycodes,
        flags=flags,
    )


def send_domain_signal(
    domain: DomainRef, pid: int, signal: int, *, flags: int = 0
) -> Operation[None]:
    """Send a signal to a process in the guest, through the guest agent.

    :param domain: the domain.
    :param pid: the process id in the guest; negative to signal a process group.
    :param signal: ``virDomainProcessSignal``, e.g. 15 for SIGTERM.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain, "domain_send_process_signal", pid_value=pid, signum=signal, flags=flags
    )


def rename_domain(
    domain: DomainRef, new_name: str, *, flags: int = 0
) -> Operation[None]:
    """Rename an inactive domain.

    :param domain: the domain; it must not be running.
    :param new_name: the new name.
    :param flags: reserved, 0.
    :raises OperationInvalidError: if the domain is running.
    """
    yield from on_domain(domain, "domain_rename", new_name=new_name, flags=flags)


def set_domain_lifecycle_action(
    domain: DomainRef, action_type: int, action: int, *, flags: int = 0
) -> Operation[None]:
    """Choose what libvirt does when the guest powers off, reboots or crashes.

    :param domain: the domain.
    :param action_type: ``virDomainLifecycle``: 0 poweroff, 1 reboot, 2 crash.
    :param action: ``virDomainLifecycleAction``: 0 destroy, 1 restart, 2 rename-
        restart,
        3 preserve, 4 coredump-destroy, 5 coredump-restart.
    :param flags: ``virDomainModificationImpact``: live, config.
    """
    yield from on_domain(
        domain,
        "domain_set_lifecycle_action",
        type=action_type,
        action=action,
        flags=flags,
    )


def set_domain_user_password(
    domain: DomainRef, user: str, password: str, *, flags: int = 0
) -> Operation[None]:
    """Set the password of a user inside the guest, through the guest agent.

    :param domain: the domain.
    :param user: the user name in the guest.
    :param password: the new password; plain text unless ``flags`` says encrypted.
    :param flags: ``virDomainSetUserPasswordFlags``: 1 if the password is encrypted.
    """
    yield from on_domain(
        domain, "domain_set_user_password", user=user, password=password, flags=flags
    )


def get_domain_autostart_once(domain: DomainRef) -> Operation[bool]:
    """Tell whether the domain is set to start at the next host boot only.

    :param domain: the domain.
    :returns: ``True`` if the one-time autostart is on.
    """
    return as_bool((yield from on_domain(domain, "domain_get_autostart_once")))


def set_domain_autostart_once(domain: DomainRef, enabled: bool) -> Operation[None]:
    """Start the domain at the next host boot only.

    :param domain: the domain.
    :param enabled: ``True`` to turn the one-time autostart on, ``False`` off.
    """
    yield from on_domain(domain, "domain_set_autostart_once", autostart=int(enabled))


def reload_domain_graphics(
    domain: DomainRef, graphics_type: int = 0, *, flags: int = 0
) -> Operation[None]:
    """Make a graphics server reload its certificates.

    :param domain: the domain.
    :param graphics_type: ``virDomainGraphicsType``: 0 sdl, 1 vnc, 2 rdp, 3 desktop,
        4 spice.
    :param flags: reserved, 0.
    """
    yield from on_domain(
        domain, "domain_graphics_reload", type=graphics_type, flags=flags
    )


def save_domain_managed(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Save the memory of a running domain to a file libvirt manages, and stop it.

    The domain restores from it on its next start.

    :param domain: the domain.
    :param flags: ``virDomainSaveRestoreFlags``: running, paused, bypass cache.
    """
    yield from on_domain(domain, "domain_managed_save", flags=flags)


def has_domain_managed_save(domain: DomainRef, *, flags: int = 0) -> Operation[bool]:
    """Tell whether the domain has a managed save image.

    :param domain: the domain.
    :param flags: reserved, 0.
    :returns: ``True`` if one exists.
    """
    return as_bool(
        (yield from on_domain(domain, "domain_has_managed_save_image", flags=flags))
    )


def remove_domain_managed_save(domain: DomainRef, *, flags: int = 0) -> Operation[None]:
    """Delete the managed save image of a domain.

    :param domain: the domain.
    :param flags: reserved, 0.
    """
    yield from on_domain(domain, "domain_managed_save_remove", flags=flags)


def get_domain_managed_save_xml(
    domain: DomainRef, *, flags: int = 0
) -> Operation[Domain]:
    """Read the configuration stored in the managed save image of a domain.

    :param domain: the domain.
    :param flags: ``virDomainXMLFlags``, e.g. secure.
    :returns: the saved domain configuration.
    """
    xml = as_text(
        (yield from on_domain(domain, "domain_managed_save_get_xml_desc", flags=flags))
    )
    return Domain.from_xml(xml)


def define_domain_managed_save_xml(
    domain: DomainRef, definition: Domain | str | None = None, *, flags: int = 0
) -> Operation[None]:
    """Replace the configuration stored in the managed save image of a domain.

    :param domain: the domain.
    :param definition: the new configuration as a model or XML; ``None`` keeps it.
    :param flags: ``virDomainSaveRestoreFlags``: running or paused on restore.
    """
    xml = None if definition is None else as_xml(definition)
    yield from on_domain(
        domain, "domain_managed_save_define_xml", dxml=xml, flags=flags
    )


def save_domain(
    domain: DomainRef,
    path: str,
    *,
    definition: Domain | str | None = None,
    flags: int = 0,
) -> Operation[None]:
    """Save the memory of a running domain to a file on the host, and stop it.

    :param domain: the domain.
    :param path: the file, on the host of the daemon.
    :param definition: a different configuration to restore with, or ``None``.
    :param flags: ``virDomainSaveRestoreFlags``: bypass cache, running, paused...
    """
    xml = None if definition is None else as_xml(definition)
    yield from on_domain(domain, "domain_save_flags", to=path, dxml=xml, flags=flags)


def restore_domain(
    path: str, *, definition: Domain | str | None = None, flags: int = 0
) -> Operation[None]:
    """Start a domain from a file made by ``save_domain``.

    :param path: the file, on the host of the daemon.
    :param definition: a different configuration to restore with, or ``None``.
    :param flags: ``virDomainSaveRestoreFlags``: running or paused afterwards.
    """
    xml = None if definition is None else as_xml(definition)
    yield Request("domain_restore_flags", {"from_": path, "dxml": xml, "flags": flags})


def get_saved_domain_xml(path: str, *, flags: int = 0) -> Operation[Domain]:
    """Read the configuration stored in a save file.

    :param path: the file, on the host of the daemon.
    :param flags: ``virDomainXMLFlags``, e.g. secure.
    :returns: the saved domain configuration.
    """
    xml = as_text(
        (
            yield Request(
                "domain_save_image_get_xml_desc", {"file": path, "flags": flags}
            )
        )
    )
    return Domain.from_xml(xml)


def define_saved_domain_xml(
    path: str, definition: Domain | str, *, flags: int = 0
) -> Operation[None]:
    """Replace the configuration stored in a save file.

    :param path: the file, on the host of the daemon.
    :param definition: the new configuration as a model or XML.
    :param flags: ``virDomainSaveRestoreFlags``: running or paused on restore.
    """
    arguments = {"file": path, "dxml": as_xml(definition), "flags": flags}
    yield Request("domain_save_image_define_xml", arguments)


def dump_domain_core(
    domain: DomainRef, path: str, *, dump_format: int = 0, flags: int = 0
) -> Operation[None]:
    """Dump the core of a domain to a file on the host, for debugging.

    :param domain: the domain.
    :param path: the file, on the host of the daemon.
    :param dump_format: ``virDomainCoreDumpFormat``: 0 raw, 1 zlib, 2 lzo, 3 snappy,
        4 kdump.
    :param flags: ``virDomainCoreDumpFlags``: crash, live, reset, ...
    """
    yield from on_domain(
        domain,
        "domain_core_dump_with_format",
        to=path,
        dumpformat=dump_format,
        flags=flags,
    )
