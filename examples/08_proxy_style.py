"""The same operations, called on a proxy that remembers the object."""

from common import make_domain

from libvirtpy.client import FakeLibvirt, LibvirtClient
from libvirtpy.rpc.errors import NoStoragePoolError

client = LibvirtClient(FakeLibvirt())
client.define_domain(make_domain("proxy1"))

# Flat style: the object is the first argument.
client.start_domain("proxy1")
client.set_domain_vcpus("proxy1", 4)

# Proxy style: client.domain(ref) fills it in, like libvirt-python's objects.
# The methods come from the same operations, so both styles always agree.
vm = client.domain("proxy1")
vm.set_vcpus(6)
vm.suspend()
print("state:", vm.get_state().name)
vm.resume()
print("xml model:", vm.lookup().vcpu)

# Proxies exist for every kind of object, e.g. a network or a pool.
pool = client.pool("missing-pool")
try:
    pool.lookup()
except NoStoragePoolError as error:
    print("no such pool:", error.message)

vm.shutdown()
vm.undefine()
