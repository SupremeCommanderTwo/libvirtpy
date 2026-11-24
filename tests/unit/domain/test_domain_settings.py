import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain import (
    Domain,
    Metadata,
    QemuArg,
    SevLaunchSecurity,
    TdxLaunchSecurity,
)


def test_cputune_pins_keep_order() -> None:
    domain = _domain(
        "<cputune><vcpupin vcpu='1' cpuset='2-3'/><vcpupin vcpu='0' cpuset='0-1'/>"
        "<quota>-1</quota></cputune>"
    )

    assert domain.cputune is not None
    assert [pin.vcpu for pin in domain.cputune.vcpupins] == [1, 0]
    assert domain.cputune.quota == -1


def test_cputune_scheduler_must_be_known() -> None:
    with pytest.raises(ValidationError):
        _domain("<cputune><vcpusched scheduler='chaos'/></cputune>")


def test_memory_backing_flags_and_hugepages() -> None:
    domain = _domain(
        "<memoryBacking><hugepages><page size='2048' unit='KiB' nodeset='0'/>"
        "</hugepages><locked/><access mode='shared'/></memoryBacking>"
    )

    backing = domain.memory_backing
    assert backing is not None
    assert backing.locked is not None
    assert backing.nosharepages is None

    assert backing.hugepages is not None
    assert backing.hugepages.pages[0].nodeset == "0"


def test_numatune_memnodes() -> None:
    domain = _domain(
        "<numatune><memory mode='strict' nodeset='0-1'/>"
        "<memnode cellid='0' mode='preferred' nodeset='0'/></numatune>"
    )

    assert domain.numatune is not None
    assert domain.numatune.memnodes[0].mode == "preferred"


def test_domain_seclabels_may_repeat() -> None:
    domain = _domain(
        "<seclabel type='dynamic' model='selinux'><label>l</label></seclabel>"
        "<seclabel type='none' model='dac'/>"
    )

    assert [label.model for label in domain.seclabels] == ["selinux", "dac"]
    assert domain.seclabels[0].label == "l"


def test_hyperv_enlightenments() -> None:
    domain = _domain(
        "<features><hyperv mode='custom'><relaxed state='on'/>"
        "<spinlocks state='on' retries='4096'/>"
        "<stimer state='on'><direct state='on'/></stimer></hyperv></features>"
    )

    assert domain.features is not None
    hyperv = domain.features.hyperv
    assert hyperv is not None

    assert hyperv.spinlocks is not None
    assert hyperv.spinlocks.retries == 4096

    assert hyperv.stimer is not None
    assert hyperv.stimer.direct is not None
    assert hyperv.stimer.direct.state is True


def test_empty_genid_is_kept() -> None:
    domain = _domain("<genid/>")

    assert domain.genid == ""
    assert b"<genid></genid>" in domain.to_xml()


def test_two_sysinfo_elements() -> None:
    domain = _domain(
        "<sysinfo type='smbios'><oemStrings><entry>a</entry></oemStrings></sysinfo>"
        "<sysinfo type='fwcfg'><entry name='n' file='/f'/></sysinfo>"
    )

    assert [sysinfo.type for sysinfo in domain.sysinfos] == ["smbios", "fwcfg"]
    assert domain.sysinfos[1].entries[0].file == "/f"


def test_launch_security_type_selects_the_variant() -> None:
    sev = _domain("<launchSecurity type='sev'><policy>0x0003</policy></launchSecurity>")
    tdx = _domain("<launchSecurity type='tdx'/>")

    assert isinstance(sev.launch_security, SevLaunchSecurity)
    assert isinstance(tdx.launch_security, TdxLaunchSecurity)


def test_qemu_commandline_uses_its_namespace() -> None:
    domain = Domain.from_xml(
        "<domain type='qemu' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>"
        "<name>vm</name><qemu:commandline><qemu:arg value='-x'/>"
        "</qemu:commandline></domain>"
    )

    assert domain.qemu_commandline is not None
    assert domain.qemu_commandline.args == [QemuArg(value="-x")]


def test_namespace_is_declared_only_where_it_is_used() -> None:
    assert b"xmlns" not in _domain("").to_xml()


def test_metadata_keeps_arbitrary_elements() -> None:
    domain = _domain(
        "<metadata><my:data xmlns:my='urn:my' k='1'><my:x/></my:data><plain/>"
        "</metadata>"
    )

    assert isinstance(domain.metadata, Metadata)
    assert len(domain.metadata.elements) == 2
    assert b"urn:my" in domain.to_xml()
    assert b"<plain/>" in domain.to_xml()


def test_metadata_can_be_built_in_python() -> None:
    domain = Domain(
        type="kvm", name="vm", metadata=Metadata(elements=["<note>hi</note>"])
    )

    assert b"<metadata><note>hi</note></metadata>" in domain.to_xml()


def _domain(body: str) -> Domain:
    return Domain.from_xml(f"<domain type='kvm'><name>vm</name>{body}</domain>")
