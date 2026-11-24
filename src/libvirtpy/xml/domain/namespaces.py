"""Extension namespaces of other drivers: ``vmware:``, ``lxc:``, ``xen:``, ``bhyve:``.

The ``qemu:`` namespace has its own module, ``libvirtpy.xml.domain.qemu``.
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel

__all__ = [
    "BHYVE_NAMESPACE",
    "LXC_NAMESPACE",
    "VMWARE_NAMESPACE",
    "XEN_NAMESPACE",
    "BhyveArg",
    "BhyveCommandline",
    "LxcNamespace",
    "LxcShare",
    "VmwareDatacenterPath",
    "XenArg",
    "XenCommandline",
]

VMWARE_NAMESPACE = "http://libvirt.org/schemas/domain/vmware/1.0"
LXC_NAMESPACE = "http://libvirt.org/schemas/domain/lxc/1.0"
XEN_NAMESPACE = "http://libvirt.org/schemas/domain/xen/1.0"
BHYVE_NAMESPACE = "http://libvirt.org/schemas/domain/bhyve/1.0"


class VmwareDatacenterPath(
    LibvirtXmlModel,
    tag="datacenterpath",
    ns="vmware",
    nsmap={"vmware": VMWARE_NAMESPACE},
):
    """``<vmware:datacenterpath>``: the datacenter of the guest on ESX."""

    value: str


class LxcShare(LibvirtXmlModel):
    """Base of the ``<lxc:share*>`` elements: share a namespace with something."""

    type: Literal["name", "pid", "netns"] = attr(name="type")
    value: str = attr(name="value")


_LXC = {"lxc": LXC_NAMESPACE}


class LxcShareNet(LxcShare, tag="sharenet", ns="lxc", nsmap=_LXC):
    """``<lxc:sharenet>``: share the network namespace."""


class LxcShareIpc(LxcShare, tag="shareipc", ns="lxc", nsmap=_LXC):
    """``<lxc:shareipc>``: share the IPC namespace."""


class LxcShareUts(LxcShare, tag="shareuts", ns="lxc", nsmap=_LXC):
    """``<lxc:shareuts>``: share the UTS namespace."""


class LxcNamespace(LibvirtXmlModel, tag="namespace", ns="lxc", nsmap=_LXC):
    """``<lxc:namespace>``: namespace sharing of an LXC container."""

    sharenet: LxcShareNet | None = element(tag="sharenet", default=None)
    shareipc: LxcShareIpc | None = element(tag="shareipc", default=None)
    shareuts: LxcShareUts | None = element(tag="shareuts", default=None)


class XenArg(LibvirtXmlModel, tag="arg", ns="xen", nsmap={"xen": XEN_NAMESPACE}):
    value: str = attr(name="value")


class XenCommandline(
    LibvirtXmlModel, tag="commandline", ns="xen", nsmap={"xen": XEN_NAMESPACE}
):
    """``<xen:commandline>``: extra arguments for the Xen toolstack."""

    args: list[XenArg] = element(tag="arg", default_factory=list)


class BhyveArg(
    LibvirtXmlModel, tag="arg", ns="bhyve", nsmap={"bhyve": BHYVE_NAMESPACE}
):
    value: str = attr(name="value")


class BhyveCommandline(
    LibvirtXmlModel, tag="commandline", ns="bhyve", nsmap={"bhyve": BHYVE_NAMESPACE}
):
    """``<bhyve:commandline>``: extra arguments for bhyve."""

    args: list[BhyveArg] = element(tag="arg", default_factory=list)
