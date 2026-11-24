import pytest
from pydantic import ValidationError

from libvirtpy.xml.backup import Backup, Checkpoint
from libvirtpy.xml.capabilities import (
    Capabilities,
    DomainCapabilities,
    StoragePoolCapabilities,
)
from libvirtpy.xml.interface import HostInterface
from libvirtpy.xml.nodedev import Device
from libvirtpy.xml.nodedev.nodedev import PciCapability, UsbCapability
from libvirtpy.xml.nwfilter import Filter, FilterBinding
from libvirtpy.xml.secret import Secret
from libvirtpy.xml.snapshot import Snapshot
from libvirtpy.xml.snapshot.snapshot import DomainReference, FileSnapshotDisk
from libvirtpy.xml.sysinfo import Sysinfo


def test_secret_usage_type_and_name() -> None:
    secret = Secret.from_xml(
        "<secret private='yes'><usage type='ceph'><name>client.admin</name></usage>"
        "</secret>"
    )

    assert secret.private is True
    assert secret.usage is not None
    assert secret.usage.name == "client.admin"


def test_secret_rejects_unknown_usage_type() -> None:
    with pytest.raises(ValidationError):
        Secret.from_xml("<secret><usage type='feelings'/></secret>")


def test_host_bridge_interface_holds_nested_interfaces() -> None:
    interface = HostInterface.from_xml(
        "<interface type='bridge' name='br0'><bridge stp='on'>"
        "<interface type='ethernet' name='eth0'/>"
        "<interface type='ethernet' name='eth1'/></bridge></interface>"
    )

    assert interface.bridge is not None
    assert [nested.name for nested in interface.bridge.interfaces] == ["eth0", "eth1"]


def test_host_interface_protocols() -> None:
    interface = HostInterface.from_xml(
        "<interface type='ethernet' name='eth0'><protocol family='ipv4'>"
        "<ip address='192.0.2.2' prefix='24'/><route gateway='192.0.2.1'/></protocol>"
        "<protocol family='ipv6'><autoconf/><dhcp peerdns='no'/></protocol></interface>"
    )

    assert [protocol.family for protocol in interface.protocols] == ["ipv4", "ipv6"]
    assert interface.protocols[1].autoconf is not None


def test_filter_rule_has_one_protocol_element() -> None:
    nwfilter = Filter.from_xml(
        "<filter name='f'><rule action='drop' direction='in'>"
        "<tcp dstportstart='22' dstportend='22'/></rule></filter>"
    )

    (rule,) = nwfilter.rules
    assert rule.tcp is not None
    assert rule.tcp.dstportstart == "22"
    assert rule.udp is None


def test_filter_rule_action_must_be_known() -> None:
    with pytest.raises(ValidationError):
        Filter.from_xml(
            "<filter name='f'><rule action='explode' direction='in'/></filter>"
        )


def test_filter_binding_requires_its_parts() -> None:
    with pytest.raises(ValidationError):
        FilterBinding.from_xml("<filterbinding/>")


def test_nodedev_capability_type_selects_the_variant() -> None:
    device = Device.from_xml(
        "<device><name>d</name>"
        "<capability type='usb'><number>0</number><class>9</class>"
        "<subclass>0</subclass><protocol>0</protocol></capability>"
        "<capability type='pci'><domain>0</domain><bus>1</bus><slot>2</slot>"
        "<function>0</function><product id='0x1'/><vendor id='0x2'/></capability>"
        "</device>"
    )

    assert [type(capability) for capability in device.capabilities] == [
        UsbCapability,
        PciCapability,
    ]


def test_nodedev_rejects_unknown_capability() -> None:
    with pytest.raises(ValidationError):
        Device.from_xml("<device><name>d</name><capability type='soul'/></device>")


def test_domain_capabilities_cpu_modes_by_name() -> None:
    caps = DomainCapabilities.from_xml(
        "<domainCapabilities><domain>kvm</domain><arch>x86_64</arch><cpu>"
        "<mode name='host-passthrough' supported='yes'/>"
        "<mode name='custom' supported='yes'><model usable='yes' vendor='Intel'>"
        "Haswell</model></mode></cpu></domainCapabilities>"
    )

    assert caps.cpu is not None
    assert [mode.name for mode in caps.cpu.modes] == ["host-passthrough", "custom"]


def test_domain_capabilities_write_blockers_after_their_model() -> None:
    caps = DomainCapabilities.from_xml(
        "<domainCapabilities><domain>kvm</domain><arch>x86_64</arch><cpu>"
        "<mode name='custom' supported='yes'>"
        "<model usable='no' vendor='Intel'>A</model>"
        "<blockers model='A'><feature name='f'/></blockers>"
        "<model usable='yes' vendor='Intel'>B</model></mode></cpu>"
        "</domainCapabilities>"
    )

    xml = caps.to_xml(encoding="unicode")

    assert isinstance(xml, str)
    assert xml.index("<blockers") < xml.index(">B</model>")


def test_host_capabilities_guest_arch_and_domains() -> None:
    caps = Capabilities.from_xml(
        "<capabilities><host><cpu><arch>x86_64</arch></cpu></host>"
        "<guest><os_type>hvm</os_type><arch name='x86_64'><wordsize>64</wordsize>"
        "<domain type='kvm'><emulator>/usr/bin/qemu</emulator></domain></arch>"
        "</guest></capabilities>"
    )

    (guest,) = caps.guests
    assert guest.arch.wordsize == "64"
    assert guest.arch.domains[0].type == "kvm"


def test_storage_pool_capabilities() -> None:
    caps = StoragePoolCapabilities.from_xml(
        "<storagepoolCapabilities><pool type='dir' supported='yes'/>"
        "</storagepoolCapabilities>"
    )

    assert caps.pools[0].supported == "yes"


def test_standalone_sysinfo_has_processors() -> None:
    sysinfo = Sysinfo.from_xml(
        "<sysinfo type='smbios'><processor><entry name='version'>x</entry></processor>"
        "<processor><entry name='version'>y</entry></processor></sysinfo>"
    )

    assert [p.entries[0].value for p in sysinfo.processors] == ["x", "y"]


def test_backup_pull_server_and_scratch() -> None:
    backup = Backup.from_xml(
        "<domainbackup mode='pull'><server transport='unix' socket='/s'/>"
        "<disks><disk name='vda' backup='yes' type='file'>"
        "<scratch file='/tmp/x'/></disk></disks></domainbackup>"
    )

    assert backup.server is not None
    assert backup.server.socket == "/s"
    assert backup.disks is not None
    assert backup.disks.disks[0].scratch is not None


def test_checkpoint_disks_and_parent() -> None:
    checkpoint = Checkpoint.from_xml(
        "<domaincheckpoint><name>c</name><creationTime>1700000000</creationTime>"
        "<disks><disk name='vda' checkpoint='bitmap' bitmap='c'/></disks>"
        "<parent><name>b</name></parent></domaincheckpoint>"
    )

    assert checkpoint.creation_time == 1700000000
    assert checkpoint.parent is not None
    assert checkpoint.parent.name == "b"


def test_snapshot_disk_type_selects_the_variant() -> None:
    snapshot = Snapshot.from_xml(
        "<domainsnapshot><name>s</name><disks>"
        "<disk name='vda' snapshot='external'><source file='/f'/></disk>"
        "<disk name='vdb' snapshot='external' type='block'><source dev='/d'/></disk>"
        "</disks></domainsnapshot>"
    )

    assert snapshot.disks is not None
    assert isinstance(snapshot.disks.disks[0], FileSnapshotDisk)
    assert snapshot.disks.disks[1].type == "block"


def test_snapshot_domain_may_be_just_a_uuid() -> None:
    snapshot = Snapshot.from_xml(
        "<domainsnapshot><domain>"
        "<uuid>c7a5fdbd-edaf-9455-926a-d65c16db1809</uuid></domain></domainsnapshot>"
    )

    assert isinstance(snapshot.domain, DomainReference)


def test_snapshot_cookie_is_kept_as_xml() -> None:
    snapshot = Snapshot.from_xml(
        "<domainsnapshot><cookie><x a='1'/></cookie></domainsnapshot>"
    )

    assert snapshot.cookie is not None
    assert snapshot.cookie.elements == ['<x a="1"/>']
