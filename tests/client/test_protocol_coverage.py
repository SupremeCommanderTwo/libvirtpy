"""Every libvirt procedure is accounted for: used, superseded, or deliberately left out.

The operations are the client's whole API. A procedure that no operation uses must
be in one of the groups below, with the reason. A new libvirt version that adds
a procedure fails this test until somebody decides which group it is in.
"""

import re
from pathlib import Path

from libvirtpy.rpc.protocol.procedures import PROCEDURES

CLIENT = Path(__file__).resolve().parents[2] / "src" / "libvirtpy" / "client"
SOURCES = [*sorted((CLIENT / "operations").glob("*.py")), CLIENT / "references.py"]

# Lookups are built from a name prefix (references.py), so no source has the full name.
LOOKUP_FAMILIES = {
    f"{kind}_lookup_by_{how}"
    for kind in ("domain", "network", "storage_pool", "nwfilter")
    for how in ("name", "uuid")
}

# What the transport itself calls while connecting.
TRANSPORT = {
    "connect_open",
    "connect_close",
    "auth_list",
    "auth_polkit",
    "auth_sasl_init",
    "auth_sasl_start",
    "auth_sasl_step",
}

# Older forms of a call; the newer procedure that the operations use does the same.
SUPERSEDED = {
    "domain_attach_device": "domain_attach_device_flags",
    "domain_detach_device": "domain_detach_device_flags",
    "domain_create": "domain_create_with_flags",
    "domain_define_xml": "domain_define_xml_flags",
    "domain_destroy": "domain_destroy_flags",
    "domain_undefine": "domain_undefine_flags",
    "domain_shutdown": "domain_shutdown_flags",
    "domain_pin_vcpu": "domain_pin_vcpu_flags",
    "domain_set_memory": "domain_set_memory_flags",
    "domain_set_vcpus": "domain_set_vcpus_flags",
    "domain_core_dump": "domain_core_dump_with_format",
    "domain_save": "domain_save_flags",
    "domain_restore": "domain_restore_flags",
    "domain_get_scheduler_parameters": "domain_get_scheduler_parameters_flags",
    "domain_set_scheduler_parameters": "domain_set_scheduler_parameters_flags",
    "domain_block_stats": "domain_block_stats_flags",
    "domain_abort_job": "domain_abort_job_flags",
    "connect_list_domains": "connect_list_all_domains",
    "connect_num_of_domains": "connect_list_all_domains",
    "connect_list_defined_domains": "connect_list_all_domains",
    "connect_num_of_defined_domains": "connect_list_all_domains",
    "connect_list_networks": "connect_list_all_networks",
    "connect_num_of_networks": "connect_list_all_networks",
    "connect_list_defined_networks": "connect_list_all_networks",
    "connect_num_of_defined_networks": "connect_list_all_networks",
    "network_create_xml": "network_create_xml_flags",
    "network_define_xml": "network_define_xml_flags",
    "connect_list_storage_pools": "connect_list_all_storage_pools",
    "connect_num_of_storage_pools": "connect_list_all_storage_pools",
    "connect_list_defined_storage_pools": "connect_list_all_storage_pools",
    "connect_num_of_defined_storage_pools": "connect_list_all_storage_pools",
    "storage_pool_list_volumes": "storage_pool_list_all_volumes",
    "storage_pool_num_of_volumes": "storage_pool_list_all_volumes",
    "storage_vol_get_info": "storage_vol_get_info_flags",
    "node_list_devices": "connect_list_all_node_devices",
    "node_num_of_devices": "connect_list_all_node_devices",
    "node_device_num_of_caps": "node_device_list_caps",
    "node_device_dettach": "node_device_detach_flags",
    "connect_list_interfaces": "connect_list_all_interfaces",
    "connect_num_of_interfaces": "connect_list_all_interfaces",
    "connect_list_defined_interfaces": "connect_list_all_interfaces",
    "connect_num_of_defined_interfaces": "connect_list_all_interfaces",
    "connect_list_secrets": "connect_list_all_secrets",
    "connect_num_of_secrets": "connect_list_all_secrets",
    "connect_list_nwfilters": "connect_list_all_nwfilters",
    "connect_num_of_nwfilters": "connect_list_all_nwfilters",
    "nwfilter_define_xml": "nwfilter_define_xml_flags",
    "domain_snapshot_num": "domain_list_all_snapshots",
    "domain_snapshot_list_names": "domain_list_all_snapshots",
    "domain_snapshot_num_children": "domain_snapshot_list_all_children",
    "domain_snapshot_list_children_names": "domain_snapshot_list_all_children",
}

# Left out on purpose: they need a feature the client does not have yet.
NOT_SUPPORTED = {
    "passing file descriptors": {
        "domain_open_graphics",
        "domain_open_graphics_fd",
        "domain_create_xml_with_files",
        "domain_create_with_files",
        "domain_fd_associate",
    },
}


def used_procedures() -> set[str]:
    """Collect the procedure names that the operations mention."""
    text = "".join(path.read_text(encoding="utf-8") for path in SOURCES)
    names = set(re.findall(r'"([a-z0-9_]+)"', text))
    return names | LOOKUP_FAMILIES


def is_event(name: str) -> bool:
    """Tell whether a procedure belongs to the event system."""
    return "event" in name or name.endswith("close_callback")


def is_migration_step(name: str) -> bool:
    """Tell whether a procedure is a step of a client-orchestrated migration."""
    return (
        name.startswith("domain_migrate_")
        and re.search(r"(prepare|perform|finish|begin|confirm)", name) is not None
    )


def test_every_procedure_is_accounted_for() -> None:
    used = used_procedures()
    left_out = {name for names in NOT_SUPPORTED.values() for name in names}

    unaccounted = sorted(
        procedure.name
        for procedure in PROCEDURES.values()
        if procedure.name not in used
        and procedure.name not in TRANSPORT
        and procedure.name not in SUPERSEDED
        and procedure.name not in left_out
        and not is_event(procedure.name)
        and not is_migration_step(procedure.name)
    )

    assert not unaccounted, f"decide what to do with: {unaccounted}"


def test_every_superseded_procedure_has_its_replacement_in_use() -> None:
    used = used_procedures()

    missing = {old: new for old, new in SUPERSEDED.items() if new not in used}

    assert not missing


def test_the_groups_name_real_procedures() -> None:
    known = {procedure.name for procedure in PROCEDURES.values()}
    named = TRANSPORT | set(SUPERSEDED) | {n for g in NOT_SUPPORTED.values() for n in g}

    assert named <= known
