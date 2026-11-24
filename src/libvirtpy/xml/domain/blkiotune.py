"""``<blkiotune>`` and ``<throttlegroups>``: block I/O tuning of the guest.

See https://libvirt.org/formatdomain.html#blkio-tuning
"""

from pydantic_xml import element

from libvirtpy.xml._base import LibvirtXmlModel

__all__ = ["BlkioDevice", "Blkiotune", "ThrottleGroup", "ThrottleGroups"]


class BlkioDevice(LibvirtXmlModel, tag="device"):
    """``<device>``: weight and limits for one host block device."""

    path: str = element(tag="path")
    weight: int | None = element(tag="weight", default=None, ge=0)
    read_iops_sec: int | None = element(tag="read_iops_sec", default=None, ge=0)
    write_iops_sec: int | None = element(tag="write_iops_sec", default=None, ge=0)
    read_bytes_sec: int | None = element(tag="read_bytes_sec", default=None, ge=0)
    write_bytes_sec: int | None = element(tag="write_bytes_sec", default=None, ge=0)


class Blkiotune(LibvirtXmlModel, tag="blkiotune"):
    """``<blkiotune>``: the default weight and per-device settings."""

    weight: int | None = element(tag="weight", default=None, ge=0)
    devices: list[BlkioDevice] = element(tag="device", default_factory=list)


class ThrottleGroup(LibvirtXmlModel, tag="throttlegroup"):
    """``<throttlegroup>``: a named set of I/O limits shared by disks."""

    group_name: str | None = element(tag="group_name", default=None)
    total_bytes_sec: int | None = element(tag="total_bytes_sec", default=None, ge=0)
    read_bytes_sec: int | None = element(tag="read_bytes_sec", default=None, ge=0)
    write_bytes_sec: int | None = element(tag="write_bytes_sec", default=None, ge=0)
    total_iops_sec: int | None = element(tag="total_iops_sec", default=None, ge=0)
    read_iops_sec: int | None = element(tag="read_iops_sec", default=None, ge=0)
    write_iops_sec: int | None = element(tag="write_iops_sec", default=None, ge=0)
    total_bytes_sec_max: int | None = element(
        tag="total_bytes_sec_max", default=None, ge=0
    )
    read_bytes_sec_max: int | None = element(
        tag="read_bytes_sec_max", default=None, ge=0
    )
    write_bytes_sec_max: int | None = element(
        tag="write_bytes_sec_max", default=None, ge=0
    )
    total_iops_sec_max: int | None = element(
        tag="total_iops_sec_max", default=None, ge=0
    )
    read_iops_sec_max: int | None = element(tag="read_iops_sec_max", default=None, ge=0)
    write_iops_sec_max: int | None = element(
        tag="write_iops_sec_max", default=None, ge=0
    )
    size_iops_sec: int | None = element(tag="size_iops_sec", default=None, ge=0)
    total_bytes_sec_max_length: int | None = element(
        tag="total_bytes_sec_max_length", default=None, ge=0
    )
    read_bytes_sec_max_length: int | None = element(
        tag="read_bytes_sec_max_length", default=None, ge=0
    )
    write_bytes_sec_max_length: int | None = element(
        tag="write_bytes_sec_max_length", default=None, ge=0
    )
    total_iops_sec_max_length: int | None = element(
        tag="total_iops_sec_max_length", default=None, ge=0
    )
    read_iops_sec_max_length: int | None = element(
        tag="read_iops_sec_max_length", default=None, ge=0
    )
    write_iops_sec_max_length: int | None = element(
        tag="write_iops_sec_max_length", default=None, ge=0
    )


class ThrottleGroups(LibvirtXmlModel, tag="throttlegroups"):
    """``<throttlegroups>``: the throttle groups of the domain. Since 9.0.0."""

    groups: list[ThrottleGroup] = element(tag="throttlegroup", default_factory=list)
