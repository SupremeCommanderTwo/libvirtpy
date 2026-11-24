"""Host information and the remaining resource types."""

from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.xml import Filter, Secret
from libvirtpy.xml.nwfilter.filter import FilterRule
from libvirtpy.xml.nwfilter.rules import TcpRule
from libvirtpy.xml.secret import SecretUsage

client = LibvirtClient(FakeLibvirt())

# the host
capabilities = client.get_capabilities()
print("guest architectures:", [g.arch.name for g in capabilities.guests])
domain_caps = client.get_domain_capabilities(virt_type="kvm")
print("max vCPUs:", domain_caps.vcpu.max if domain_caps.vcpu else None)
print("pool types:", [p.type for p in client.get_storage_pool_capabilities().pools])
print("system:", client.get_sysinfo().system)

# host devices
for device in client.list_node_devices(capability="pci"):
    print("device:", device.name)

# a network filter
client.define_nwfilter(
    Filter(
        name="allow-ssh",
        rules=[
            FilterRule(action="accept", direction="in", tcp=TcpRule(dstportstart="22"))
        ],
    )
)
print("filters:", [f.name for f in client.list_nwfilters()])

# a secret: the description is XML, the value is separate
secret = client.define_secret(
    Secret(private=False, usage=SecretUsage(type="ceph", name="client.admin"))
)
client.set_secret_value(secret, b"AQBexample==")
print("secret value:", client.get_secret_value(secret))
