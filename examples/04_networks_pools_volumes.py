"""A virtual network, a storage pool, and volumes in it."""

from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.xml._shared.storage import Capacity
from libvirtpy.xml.network import Network, NetworkForward, NetworkIp
from libvirtpy.xml.network.network import DhcpRange, NetworkDhcp
from libvirtpy.xml.storage import Pool, Volume
from libvirtpy.xml.storage.pool import PoolTarget
from libvirtpy.xml.storage.volume import VolumeFormat, VolumeTarget

client = LibvirtClient(FakeLibvirt())

# a NAT network with DHCP
network = client.define_network(
    Network(
        name="lab",
        forward=NetworkForward(mode="nat"),
        ips=[
            NetworkIp(
                address="192.168.50.1",
                netmask="255.255.255.0",
                dhcp=NetworkDhcp(
                    ranges=[DhcpRange(start="192.168.50.100", end="192.168.50.200")]
                ),
            )
        ],
    )
)
client.start_network(network)
client.set_network_autostart("lab", True)
print("network:", network.name, "uuid", network.uuid)
print("active networks:", [n.name for n in client.list_networks(active=True)])

# a directory pool and volumes
pool = client.define_pool(
    Pool(type="dir", name="images", target=PoolTarget(path="/srv/images"))
)
client.build_pool(pool)
client.start_pool(pool)

disk = client.create_pool_volume(
    "images",
    Volume(
        name="disk1.qcow2",
        capacity=Capacity(value=10, unit="GiB"),
        target=VolumeTarget(format=VolumeFormat(type="qcow2")),
    ),
)
print("created volume:", disk.name, "at", disk.target.path if disk.target else None)

resized = client.resize_pool_volume("images", "disk1.qcow2", 20 * 1024**3)
print("new capacity:", resized.capacity)

print("volumes:", [v.name for v in client.list_pool_volumes("images")])
client.delete_pool_volume("images", disk)
print("volumes after delete:", [v.name for v in client.list_pool_volumes("images")])

# Tear down: stop before undefine.
client.destroy_pool("images")
client.undefine_pool("images")
client.destroy_network("lab")
client.undefine_network("lab")
