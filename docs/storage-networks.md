# Networks, storage pools and volumes

## A virtual network

```python
from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.xml.network import Network, NetworkForward, NetworkIp
from libvirtpy.xml.network.network import DhcpRange, NetworkDhcp

client = LibvirtClient(FakeLibvirt())

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
print([n.name for n in client.list_networks(active=True)])
```

`define_network` stores the network; `start_network` brings it up. `create_network`
makes a transient one. A network has *ports* (`NetworkPort` models, one per connected
interface) and DHCP leases; see the `network_port` and `network_info` operations in
{doc}`reference/client`.

## A storage pool and its volumes

```python
from libvirtpy.xml._shared.storage import Capacity
from libvirtpy.xml.storage import Pool, Volume
from libvirtpy.xml.storage.pool import PoolTarget
from libvirtpy.xml.storage.volume import VolumeFormat, VolumeTarget

pool = client.define_pool(
    Pool(type="dir", name="images", target=PoolTarget(path="/srv/images"))
)
client.build_pool(pool)  # creates the directory
client.start_pool(pool)

disk = client.create_pool_volume(
    "images",
    Volume(
        name="disk1.qcow2",
        capacity=Capacity(value=10, unit="GiB"),
        target=VolumeTarget(format=VolumeFormat(type="qcow2")),
    ),
)
print(disk.target.path)

client.resize_pool_volume("images", "disk1.qcow2", 20 * 1024**3)  # bytes
print([v.name for v in client.list_pool_volumes("images")])
client.delete_pool_volume("images", disk)
```

Tear down in reverse: `destroy_pool` (stop) and `undefine_pool`, `destroy_network`
and `undefine_network`.

## Move data in and out of a volume

Upload and download are streams (they need a real daemon):

```python
import shutil

with client.download_pool_volume("images", "disk1.qcow2") as source:
    with open("disk1.qcow2", "wb") as target:
        shutil.copyfileobj(source, target)

with open("disk1.qcow2", "rb") as source:
    with client.upload_pool_volume("images", "copy.qcow2") as target:
        shutil.copyfileobj(source, target)
```

## Other resources

The same shape (`define_*`, `lookup_*`, `list_*`, `undefine_*`) covers secrets,
network filters and their bindings, host interfaces and host devices: see
`examples/09_host_and_other_resources.py`. A secret's description is XML while its
value is set separately with `set_secret_value`.
