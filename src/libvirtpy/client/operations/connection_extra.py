"""Operations on the connection: driver information, CPU comparison, conversions."""

from libvirtpy.client.operations._common import (
    as_bool,
    as_int,
    as_list,
    as_struct,
    as_text,
    as_xml,
)
from libvirtpy.client.transport import Operation, Request
from libvirtpy.rpc.protocol import types
from libvirtpy.rpc.typed_params import TypedValue, from_wire, to_wire
from libvirtpy.xml.domain import Domain

__all__ = [
    "baseline_cpu",
    "baseline_hypervisor_cpu",
    "compare_cpu",
    "compare_hypervisor_cpu",
    "convert_domain_from_native",
    "convert_domain_to_native",
    "get_all_domain_stats",
    "get_cpu_model_names",
    "get_driver_type",
    "get_library_version",
    "get_max_vcpus",
    "get_uri",
    "is_connection_secure",
    "set_connection_identity",
    "supports_feature",
]


def get_driver_type() -> Operation[str]:
    """Return the name of the hypervisor driver.

    :returns: e.g. ``QEMU``.
    """
    return as_text((yield Request("connect_get_type")))


def get_uri() -> Operation[str]:
    """Return the URI the daemon reports for the connection.

    :returns: e.g. ``qemu:///system``.
    """
    return as_text((yield Request("connect_get_uri")))


def get_library_version() -> Operation[int]:
    """Return the version of the libvirt daemon.

    :returns: ``major * 1_000_000 + minor * 1_000 + release``.
    """
    return as_int((yield Request("connect_get_lib_version")))


def get_max_vcpus(virt_type: str | None = None) -> Operation[int]:
    """Return how many virtual CPUs the hypervisor supports for one domain.

    :param virt_type: the domain type (``kvm``, ``qemu``); ``None`` for the default.
    :returns: the limit.
    """
    return as_int((yield Request("connect_get_max_vcpus", {"type": virt_type})))


def supports_feature(feature: int) -> Operation[bool]:
    """Tell whether the driver supports a feature.

    :param feature: ``virDrvFeature``, e.g. 3 migration v1, 7 migration v2.
    :returns: ``True`` if supported.
    """
    return as_bool((yield Request("connect_supports_feature", {"feature": feature})))


def is_connection_secure() -> Operation[bool]:
    """Tell whether the connection is encrypted or local.

    :returns: ``True`` if it is secure.
    """
    return as_bool((yield Request("connect_is_secure")))


def compare_cpu(cpu: str, *, flags: int = 0) -> Operation[int]:
    """Compare a CPU description with the CPU of the host.

    :param cpu: the ``<cpu>`` XML to compare.
    :param flags: ``virConnectCompareCPUFlags``: fail if incomparable, ...
    :returns: ``virCPUCompareResult``: 0 incompatible, 1 identical, 2 superset.
    """
    reply = yield Request("connect_compare_cpu", {"xml": cpu, "flags": flags})
    return as_int(reply)


def baseline_cpu(cpus: list[str], *, flags: int = 0) -> Operation[str]:
    """Compute a CPU that all the given CPUs can run.

    :param cpus: the ``<cpu>`` XML of each CPU.
    :param flags: ``virConnectBaselineCPUFlags``: expand features, migratable.
    :returns: the common ``<cpu>`` XML.
    """
    reply = yield Request("connect_baseline_cpu", {"xml_cpus": cpus, "flags": flags})
    return as_text(reply)


def get_cpu_model_names(arch: str) -> Operation[list[str]]:
    """List the CPU models known for an architecture.

    :param arch: e.g. ``x86_64``.
    :returns: the model names.
    """
    reply = yield Request(
        "connect_get_cpu_model_names", {"arch": arch, "need_results": 1, "flags": 0}
    )
    return [as_text(name) for name in as_list(reply)]


def compare_hypervisor_cpu(
    cpu: str,
    *,
    emulator: str | None = None,
    arch: str | None = None,
    machine: str | None = None,
    virt_type: str | None = None,
    flags: int = 0,
) -> Operation[int]:
    """Compare a CPU description with what the hypervisor can provide.

    :param cpu: the ``<cpu>`` XML to compare.
    :param emulator: the emulator binary, or ``None`` for the default.
    :param arch: the architecture, or ``None`` for the default.
    :param machine: the machine type, or ``None`` for the default.
    :param virt_type: the domain type, or ``None`` for the default.
    :param flags: ``virConnectCompareCPUFlags``.
    :returns: ``virCPUCompareResult``: 0 incompatible, 1 identical, 2 superset.
    """
    reply = yield Request(
        "connect_compare_hypervisor_cpu",
        {
            "emulator": emulator,
            "arch": arch,
            "machine": machine,
            "virttype": virt_type,
            "xml_cpu": cpu,
            "flags": flags,
        },
    )
    return as_int(reply)


def baseline_hypervisor_cpu(
    cpus: list[str],
    *,
    emulator: str | None = None,
    arch: str | None = None,
    machine: str | None = None,
    virt_type: str | None = None,
    flags: int = 0,
) -> Operation[str]:
    """Compute a CPU that the hypervisor can provide and all the given CPUs have.

    :param cpus: the ``<cpu>`` XML of each CPU.
    :param emulator: the emulator binary, or ``None`` for the default.
    :param arch: the architecture, or ``None`` for the default.
    :param machine: the machine type, or ``None`` for the default.
    :param virt_type: the domain type, or ``None`` for the default.
    :param flags: ``virConnectBaselineCPUFlags``.
    :returns: the common ``<cpu>`` XML.
    """
    reply = yield Request(
        "connect_baseline_hypervisor_cpu",
        {
            "emulator": emulator,
            "arch": arch,
            "machine": machine,
            "virttype": virt_type,
            "xml_cpus": cpus,
            "flags": flags,
        },
    )
    return as_text(reply)


def convert_domain_from_native(
    native_format: str, native_config: str, *, flags: int = 0
) -> Operation[Domain]:
    """Convert a hypervisor's own configuration to a domain description.

    :param native_format: e.g. ``qemu-argv``.
    :param native_config: the configuration in that format.
    :param flags: reserved, 0.
    :returns: the domain.
    """
    reply = yield Request(
        "connect_domain_xml_from_native",
        {
            "native_format": native_format,
            "native_config": native_config,
            "flags": flags,
        },
    )
    return Domain.from_xml(as_text(reply))


def convert_domain_to_native(
    native_format: str, domain: Domain | str, *, flags: int = 0
) -> Operation[str]:
    """Convert a domain description to a hypervisor's own configuration.

    :param native_format: e.g. ``qemu-argv``.
    :param domain: the domain, as a model or XML.
    :param flags: reserved, 0.
    :returns: the configuration in that format (for QEMU, the command line).
    """
    reply = yield Request(
        "connect_domain_xml_to_native",
        {
            "native_format": native_format,
            "domain_xml": as_xml(domain),
            "flags": flags,
        },
    )
    return as_text(reply)


def get_all_domain_stats(
    stats: int = 0, *, flags: int = 0
) -> Operation[dict[str, dict[str, TypedValue]]]:
    """Return the statistics of all domains in one call.

    :param stats: ``virDomainStatsTypes`` bits (state, cpu, balloon, vcpu,
        interface,
        block, perf...); 0 for all.
    :param flags: ``virConnectGetAllDomainStatsFlags``: which domains to include.
    :returns: for each domain name its statistics by name (``state.state``,
        ``balloon.current``...).
    """
    reply = yield Request(
        "connect_get_all_domain_stats", {"doms": [], "stats": stats, "flags": flags}
    )
    records = [as_struct(item, types.DomainStatsRecord) for item in as_list(reply)]
    return {record.dom.name: from_wire(record.params) for record in records}


def set_connection_identity(
    parameters: dict[str, TypedValue], *, flags: int = 0
) -> Operation[None]:
    """Tell the daemon who the client acts for (when it connects for someone else).

    :param parameters: e.g. ``user-name``, ``unix-user-id``, ``selinux-context``.
    :param flags: reserved, 0.
    """
    yield Request(
        "connect_set_identity", {"params": to_wire(parameters), "flags": flags}
    )
