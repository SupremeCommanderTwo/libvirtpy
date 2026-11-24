import pytest
from pydantic import ValidationError

from libvirtpy.xml.network import (
    DhcpHost,
    Network,
    NetworkForward,
    NetworkIp,
    NetworkPort,
    PortPlug,
)


def test_network_minimal() -> None:
    network = Network.from_xml("<network><name>default</name></network>")

    assert network.name == "default"
    assert network.forward is None
    assert network.ips == []


def test_network_without_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Network.from_xml("<network/>")


def test_forward_mode_must_be_known() -> None:
    with pytest.raises(ValidationError):
        Network.from_xml("<network><name>n</name><forward mode='teleport'/></network>")


def test_ip_with_netmask_and_dhcp_range() -> None:
    network = Network.from_xml(
        "<network><name>n</name><ip address='192.0.2.1' netmask='255.255.255.0'>"
        "<dhcp><range start='192.0.2.2' end='192.0.2.254'/></dhcp></ip></network>"
    )

    (ip,) = network.ips
    assert isinstance(ip, NetworkIp)
    assert ip.netmask == "255.255.255.0"
    assert ip.dhcp is not None
    assert ip.dhcp.ranges[0].end == "192.0.2.254"


def test_dhcp_host_keeps_mac_or_duid() -> None:
    network = Network.from_xml(
        "<network><name>n</name><ip address='1.1.1.1'><dhcp>"
        "<host mac='52:54:00:00:00:01' ip='1.1.1.2'/>"
        "<host id='0:1:2' ip='2001:db8::2'/></dhcp></ip></network>"
    )

    assert network.ips[0].dhcp is not None
    hosts = network.ips[0].dhcp.hosts
    assert hosts == [
        DhcpHost(mac="52:54:00:00:00:01", ip="1.1.1.2"),
        DhcpHost(id="0:1:2", ip="2001:db8::2"),
    ]


def test_hostdev_forward_pool_lists_pci_addresses() -> None:
    network = Network.from_xml(
        "<network><name>n</name><forward mode='hostdev' managed='yes'>"
        "<driver name='vfio'/><address type='pci' domain='0x0000' bus='0x03' "
        "slot='0x00' function='0x1'/></forward></network>"
    )

    assert isinstance(network.forward, NetworkForward)
    assert network.forward.addresses[0].function == "0x1"


def test_dnsmasq_options_use_their_namespace() -> None:
    xml = (
        "<network xmlns:dnsmasq='http://libvirt.org/schemas/network/dnsmasq/1.0'>"
        "<name>n</name><dnsmasq:options><dnsmasq:option value='a=b'/>"
        "</dnsmasq:options></network>"
    )

    network = Network.from_xml(xml)

    assert network.dnsmasq_options is not None
    assert network.dnsmasq_options.options[0].value == "a=b"


def test_dns_domain_register_attribute() -> None:
    network = Network.from_xml(
        "<network><name>n</name><domain name='x.test' register='no'/></network>"
    )

    assert network.domain is not None
    assert network.domain.registered is False


def test_network_port_plug_by_type() -> None:
    from libvirtpy.xml.network import NetworkPort as Port

    port = Port.from_xml(
        "<networkport><uuid>c7a5fdbd-edaf-9455-926a-d65c16db1809</uuid>"
        "<owner><name>vm</name><uuid>d7a5fdbd-edaf-9455-926a-d65c16db1809</uuid></owner>"
        "<mac address='52:54:00:00:00:01'/><plug type='bridge' bridge='br0'/>"
        "</networkport>"
    )

    assert isinstance(port, NetworkPort)
    assert port.plug == PortPlug(type="bridge", bridge="br0")
