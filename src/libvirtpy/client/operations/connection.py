"""Operations on the connection and the host: version, capabilities, sysinfo."""

from libvirtpy.client.operations._common import (
    as_int,
    as_text,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.xml.capabilities import (
    Capabilities,
    DomainCapabilities,
    StoragePoolCapabilities,
)
from libvirtpy.xml.sysinfo import Sysinfo

__all__ = [
    "get_capabilities",
    "get_domain_capabilities",
    "get_hostname",
    "get_storage_pool_capabilities",
    "get_sysinfo",
    "get_version",
]


def get_version() -> Operation[int]:
    """Return the hypervisor version.

    :returns: the version as ``major * 1_000_000 + minor * 1_000 + release``.
    """
    return as_int((yield Request("connect_get_version")))


def get_hostname() -> Operation[str]:
    """Return the host name of the machine the daemon runs on.

    :returns: the host name.
    """
    return as_text((yield Request("connect_get_hostname")))


def get_capabilities() -> Operation[Capabilities]:
    """Return what the host and its hypervisors can do.

    :returns: the host capabilities.
    """
    xml = as_text((yield Request("connect_get_capabilities")))
    return Capabilities.from_xml(xml)


def get_domain_capabilities(
    *,
    emulator_binary: str | None = None,
    arch: str | None = None,
    machine: str | None = None,
    virt_type: str | None = None,
) -> Operation[DomainCapabilities]:
    """Return what a hypervisor supports for a domain.

    :param emulator_binary: the emulator, or ``None`` for the default.
    :param arch: the guest architecture, or ``None`` for the default.
    :param machine: the machine type, or ``None`` for the default.
    :param virt_type: the domain type (``kvm``, ``qemu``), or ``None``.
    :returns: the domain capabilities.
    """
    arguments = {
        "emulatorbin": emulator_binary,
        "arch": arch,
        "machine": machine,
        "virttype": virt_type,
        "flags": 0,
    }
    xml = as_text((yield Request("connect_get_domain_capabilities", arguments)))
    return DomainCapabilities.from_xml(xml)


def get_storage_pool_capabilities() -> Operation[StoragePoolCapabilities]:
    """Return what each storage pool type supports.

    :returns: the storage pool capabilities.
    """
    xml = as_text(
        (yield Request("connect_get_storage_pool_capabilities", {"flags": 0}))
    )
    return StoragePoolCapabilities.from_xml(xml)


def get_sysinfo() -> Operation[Sysinfo]:
    """Return the host's SMBIOS data.

    :returns: the host system information.
    """
    xml = as_text((yield Request("connect_get_sysinfo", {"flags": 0})))
    return Sysinfo.from_xml(xml)
