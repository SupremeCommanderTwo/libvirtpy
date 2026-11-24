"""``<storagepoolCapabilities>``: what each storage pool type supports.

Read-only: libvirt generates it, you only parse it.
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel

__all__ = [
    "PoolCapabilities",
    "PoolCapsDefaultFormat",
    "PoolCapsEnum",
    "PoolCapsOptions",
    "StoragePoolCapabilities",
]


class PoolCapsDefaultFormat(LibvirtXmlModel, tag="defaultFormat"):
    type: str = attr(name="type")


class PoolCapsEnum(LibvirtXmlModel, tag="enum"):
    name: str = attr(name="name")
    values: list[str] = element(tag="value", default_factory=list)


class PoolCapsOptions(LibvirtXmlModel):
    """Base of ``<poolOptions>`` and ``<volOptions>``."""

    default_format: PoolCapsDefaultFormat | None = element(
        tag="defaultFormat", default=None
    )
    enums: list[PoolCapsEnum] = element(tag="enum", default_factory=list)


class PoolOptions(PoolCapsOptions, tag="poolOptions"):
    """``<poolOptions>``: formats the pool itself can have."""


class VolOptions(PoolCapsOptions, tag="volOptions"):
    """``<volOptions>``: formats the volumes of the pool can have."""


class PoolCapabilities(LibvirtXmlModel, tag="pool"):
    """``<pool>``: the capabilities of one pool type."""

    type: str = attr(name="type")
    supported: Literal["yes", "no"] = attr(name="supported")
    pool_options: PoolOptions | None = element(tag="poolOptions", default=None)
    vol_options: VolOptions | None = element(tag="volOptions", default=None)


class StoragePoolCapabilities(LibvirtXmlModel, tag="storagepoolCapabilities"):
    """``<storagepoolCapabilities>``: the capabilities of every pool type."""

    pools: list[PoolCapabilities] = element(tag="pool", default_factory=list)
