"""The ``qemu:`` XML namespace: QEMU specific extensions of ``<domain>``.

They are not part of the core model; ``Domain`` wires them in explicitly.

See https://libvirt.org/drvqemu.html#pass-through-of-arbitrary-qemu-commands
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel

__all__ = [
    "QEMU_NAMESPACE",
    "QemuArg",
    "QemuCapabilities",
    "QemuCapability",
    "QemuCommandline",
    "QemuDeprecation",
    "QemuEnv",
    "QemuOverride",
    "QemuOverrideDevice",
    "QemuOverrideProperty",
]

QEMU_NAMESPACE = "http://libvirt.org/schemas/domain/qemu/1.0"
_NSMAP = {"qemu": QEMU_NAMESPACE}


class QemuArg(LibvirtXmlModel, tag="arg", ns="qemu", nsmap=_NSMAP):
    """``<qemu:arg>``: one extra command line argument."""

    value: str = attr(name="value")


class QemuEnv(LibvirtXmlModel, tag="env", ns="qemu", nsmap=_NSMAP):
    """``<qemu:env>``: an environment variable of the QEMU process."""

    name: str = attr(name="name")
    value: str | None = attr(name="value", default=None)


class QemuCommandline(LibvirtXmlModel, tag="commandline", ns="qemu", nsmap=_NSMAP):
    """``<qemu:commandline>``: extra arguments and environment for QEMU."""

    args: list[QemuArg] = element(tag="arg", default_factory=list)
    envs: list[QemuEnv] = element(tag="env", default_factory=list)


class QemuCapability(LibvirtXmlModel, ns="qemu", nsmap=_NSMAP):
    """Base of ``<qemu:add>`` and ``<qemu:del>``."""

    capability: str = attr(name="capability")


class QemuAdd(QemuCapability, tag="add", ns="qemu", nsmap=_NSMAP):
    """``<qemu:add>``: force a QEMU capability on."""


class QemuDel(QemuCapability, tag="del", ns="qemu", nsmap=_NSMAP):
    """``<qemu:del>``: force a QEMU capability off."""


class QemuCapabilities(LibvirtXmlModel, tag="capabilities", ns="qemu", nsmap=_NSMAP):
    """``<qemu:capabilities>``: override the detected QEMU capabilities."""

    adds: list[QemuAdd] = element(tag="add", default_factory=list)
    dels: list[QemuDel] = element(tag="del", default_factory=list)


class QemuDeprecation(LibvirtXmlModel, tag="deprecation", ns="qemu", nsmap=_NSMAP):
    """``<qemu:deprecation>``: what to do about deprecated QEMU features."""

    behavior: Literal["none", "omit", "reject", "crash"] = attr(name="behavior")


class QemuOverrideProperty(LibvirtXmlModel, tag="property", ns="qemu", nsmap=_NSMAP):
    """``<qemu:property>``: set a device property."""

    name: str = attr(name="name")
    type: Literal["string", "signed", "unsigned", "bool", "remove"] = attr(name="type")
    value: str | None = attr(name="value", default=None)


class QemuOverrideFrontend(LibvirtXmlModel, tag="frontend", ns="qemu", nsmap=_NSMAP):
    properties: list[QemuOverrideProperty] = element(
        tag="property", default_factory=list
    )


class QemuOverrideDevice(LibvirtXmlModel, tag="device", ns="qemu", nsmap=_NSMAP):
    """``<qemu:device>``: overrides for one device, by its alias."""

    alias: str = attr(name="alias")
    frontend: QemuOverrideFrontend | None = element(tag="frontend", default=None)


class QemuOverride(LibvirtXmlModel, tag="override", ns="qemu", nsmap=_NSMAP):
    """``<qemu:override>``: device property overrides."""

    devices: list[QemuOverrideDevice] = element(tag="device", default_factory=list)
